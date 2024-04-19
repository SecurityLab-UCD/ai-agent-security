from bfv.bfv_evaluator import BFVEvaluator
from bfv.int_encoder import IntegerEncoder
from bfv.bfv_decryptor import BFVDecryptor
from bfv.bfv_encryptor import BFVEncryptor
from util.ciphertext import Ciphertext
import os
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.base import Runnable
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain.pydantic_v1 import BaseModel, Field
import re

from HE_data.HE_data import load_encoder, load_ciphertext, serialize_ciphertext


def initialize_ciphertexts(dir: str) -> dict[int, Ciphertext]:
    """
    Load ciphertext files from a directory into a dictionary mapping number
    to ciphertext object.
    """
    ctxts = {}
    ciphertext_regex = "([0-9]+)\.txt"
    for file in os.listdir(f"./{dir}"):
        match = re.match(ciphertext_regex, file)
        if match:
            ctxts[int(match[1])] = load_ciphertext(filename=f"{dir}/{file}")
    return ctxts


### Tools ###
def add_encrypted_numbers(nums: list[str]) -> str:
    """
    Adds py_fhe ciphertexts and returns the sum.

        Args:
            nums (list[str]): List of ciphertext serializations to add

        Returns:
            (str): Ciphertext serialization of the sum
    """
    if not nums:
        raise ValueError("Empty list passed to add_encrypted_numbers")
    params, key_generator = load_encoder("HE_data/HE.txt")
    encoder = IntegerEncoder(params, 10)
    encryptor = BFVEncryptor(params, key_generator.public_key)
    evaluator = BFVEvaluator(params)
    sum = encryptor.encrypt(encoder.encode(0))
    for num in nums:
        sum = evaluator.add(sum, load_ciphertext(serialization=num))
    return serialize_ciphertext(sum)


class AddEncryptedNumbersInput(BaseModel):
    nums: list[str] = Field(
        description="List of homomorphically-encrypted ciphertexts to add together."
    )


add_numbers = StructuredTool.from_function(
    func=add_encrypted_numbers,
    name="add_encrypted_numbers",
    description="""
    Returns a ciphertext representing the sum of the homomorphically-encrypted ciphertexts of the input list.
    The whole string that is returned is the result, not just part of it.
    """,
    args_schema=AddEncryptedNumbersInput,
)


def multiply_encrypted_numbers(nums: list[str]) -> str:
    """
    Multiplies py_fhe ciphertexts and returns the sum.

        Args:
            nums (list[str]): List of ciphertext serializations to add

        Returns:
            (str): Ciphertext serialization of the product
    """
    params, key_generator = load_encoder("HE_data/HE.txt")
    encoder = IntegerEncoder(params, 10)
    encryptor = BFVEncryptor(params, key_generator.public_key)
    evaluator = BFVEvaluator(params)
    prod = encryptor.encrypt(encoder.encode(1))
    for num in nums:
        prod = evaluator.multiply(
            prod, load_ciphertext(serialization=num), key_generator.relin_key
        )
    return serialize_ciphertext(prod)


class MultiplyEncryptedNumbersInput(BaseModel):
    nums: list[str] = Field(
        description="List of homomorphically-encrypted ciphertexts to multiply together."
    )


multiply_numbers = StructuredTool.from_function(
    func=multiply_encrypted_numbers,
    name="multiply_encrypted_numbers",
    description="""
    Returns the ciphertext representing the product of the homomorphically-encrypted
    ciphertexts of the input list.
    The whole string that is returned is the result, not just part of it.
    """,
    args_schema=MultiplyEncryptedNumbersInput,
)

tools = [add_numbers, multiply_numbers]  # List of tools


def create_agent() -> Runnable:
    """
    Creates a gpt-3.5-turbo agent runnable with access to tools add_numbers
    and multiply_numbers.
    """
    # Need to set OPENAI_API_KEY environment variable: export OPENAI_API_KEY="<key>"
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    template_query = """Based on the numbers below, return a response to the user's question:
    Numbers: {numbers}
    Question: {question}
    """
    prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are an assistant that performs calculations with lab data.
                The data is provided as a list in the user query and the user
                will specify the indices of the numbers to use using 0-based indexing.
                For example, 0 would be the first element of the list and 4 would be
                the fifth element of the list.
                Format your response as:
                <calculation result>
                """,
            ),
            ("human", template_query),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = (
        {
            "question": lambda x: x["question"],
            "numbers": lambda x: x["numbers"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
        }
        | prompt_template
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
    )
    return agent


def post_process(response: str) -> str:
    """Replaces ciphertext in LLM-generated response with decrypted number."""
    params, key_generator = load_encoder("HE_data/HE.txt")
    encoder = IntegerEncoder(params, 10)
    decryptor = BFVDecryptor(params, key_generator.secret_key)
    return str(
        encoder.decode(decryptor.decrypt(load_ciphertext(serialization=response)))
    )


def main():
    # Load ciphertext objects
    ctxts = initialize_ciphertexts("HE_data")

    user_query = input("What would you like to do today?\n>>> ")

    agent_executor = AgentExecutor(agent=create_agent(), tools=tools, verbose=True)
    result = agent_executor.invoke(
        {
            "question": user_query,
            "numbers": [serialize_ciphertext(x) for x in ctxts.values()],
        }
    )
    print(f"Agent output: " + result["output"])
    print("Postprocessed output: " + post_process(result["output"]))

    keys = list(ctxts.keys())
    indices = [int(x) for x in re.findall(r"\d+", user_query)]
    print("Numbers:", end=" ")
    if "sum" in user_query:
        check = 0
        for idx in indices:
            print(keys[idx], end=" ")
            check += keys[idx]
        print(f"\nSum: {check}")
    if "product" in user_query:
        check = 1
        for idx in indices:
            print(keys[idx], end=" ")
            check *= keys[idx]
        print(f"\nProduct: {check}")


if __name__ == "__main__":
    main()
