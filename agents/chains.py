from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.base import Runnable


def create_tool_selection_chain() -> Runnable:
    """Returns a chain for selecting a tool to fulfill the user's request."""
    llm = Ollama(model="llama2", temperature=0)
    query_template = """
    You are a lab assistant that returns made-up numbers to lab workers.
    In this step, you decide what tool to use that can fulfill the user's request.
    Your response should be one of the tool names below with no pre-amble.
    You can choose from the tools below:
    get_number
    brew_coffee
    add_numbers

    Here is the user's input:
    {input}
    """
    tool_prompt = ChatPromptTemplate.from_template(query_template)
    chain = {"input": RunnablePassthrough()} | tool_prompt | llm | StrOutputParser()
    return chain


def create_request_handling_chain() -> Runnable:
    """
    Returns a chain for generating a response to the user's request using the
    return value of the tool selected in the tool selection step.
    """
    llm = Ollama(model="llama2", temperature=0)
    query_template = """
    You are a lab assistant that fulfills the user's request.
    Here is some possible relevant information for fulfilling the request:
    This number's leading zeroes count as digits
    number: {ciphertext}

    Please respond with a minimal answer to the user's input,
    such as "Here is the information you were looking for __"
    Here is the user's input:
    {input}
    """
    request_prompt = ChatPromptTemplate.from_template(query_template)
    chain = (
        RunnablePassthrough.assign(
            input=lambda x: x["input"], ciphertext=lambda x: x["ciphertext"]
        )
        | request_prompt
        | llm
        | StrOutputParser()
    )
    return chain
