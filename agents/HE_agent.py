import argparse
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
import os
import re

from HE_data.HE_data import load_encoder, load_ciphertext, serialize_ciphertext
from bfv.bfv_evaluator import BFVEvaluator
from bfv.int_encoder import IntegerEncoder
from bfv.bfv_decryptor import BFVDecryptor
from bfv.bfv_encryptor import BFVEncryptor
from util.ciphertext import Ciphertext


def initialize_ciphertexts(dir: str) -> dict[int, Ciphertext]:
    """
    Load ciphertext files from a directory into a dictionary mapping number
    to ciphertext object.
    """
    ctxts = {}
    ciphertext_regex = r"([0-9]+)\.txt"
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
    params, key_generator = load_encoder("HE_data/HE.txt")
    encoder = IntegerEncoder(params, 10)
    encryptor = BFVEncryptor(params, key_generator.public_key)
    evaluator = BFVEvaluator(params)
    # For some reason the library doesn't work if I initialize sum to 0
    if not nums:
        return serialize_ciphertext(encryptor.encrypt(encoder.encode(0)))
    sum = load_ciphertext(nums[0])
    for i in range(1, len(nums)):
        sum = evaluator.add(sum, load_ciphertext(serialization=nums[i]))
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
    # For some reason the library doesn't work if I initialize prod to 1
    if not nums:
        return serialize_ciphertext(encryptor.encrypt(encoder.encode(1)))
    prod = load_ciphertext(nums[0])
    for i in range(1, len(nums)):
        prod = evaluator.multiply(
            prod, load_ciphertext(serialization=nums[i]), key_generator.relin_key
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


def create_agent(model_name: str = "gpt-3.5-turbo") -> Runnable:
    """
    Creates an agent runnable with access to the tools add_numbers and
    multiply_numbers.

        Args:
            model_name (str): OpenAI LLM name for agent reasoning

        Returns:
            (Runnable): Langchain runnable representing agent
    """
    # Need to set OPENAI_API_KEY environment variable: export OPENAI_API_KEY="<key>"
    llm = ChatOpenAI(model=model_name, temperature=0)
    llm_with_tools = llm.bind_tools([add_numbers, multiply_numbers])

    template_query = """Based on the numbers below, return a response to the user's question without preamble:
    Numbers: {numbers}
    Question: {question}

    Result:
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


def main(args):
    # Load ciphertext objects
    ctxts = initialize_ciphertexts("HE_data")

    user_query = input("What would you like to do today?\n>>> ")

    agent_executor = AgentExecutor(
        agent=create_agent(args.model),
        tools=[add_numbers, multiply_numbers],
        verbose=True,
    )
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["gpt-3.5-turbo", "gpt-4-turbo"],
        default="gpt-3.5-turbo",
        help="LLM for agent reasoning",
    )

    args = parser.parse_args()
    main(args)
