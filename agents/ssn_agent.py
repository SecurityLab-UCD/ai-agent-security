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
import pyffx
import re
import sys

from agents.chains import create_tool_selection_chain, create_request_handling_chain


# Template class for FPE Agents
class FormatPreservingAgent:
    def __init__(self):
        raise NotImplementedError

    def encrypt(secret_key: str, value: str):
        raise NotImplementedError

    def decrypt(secret_key: str, ciphertext: str):
        raise NotImplementedError


class SSNAgent(FormatPreservingAgent):
    def __init__(self, secretkeys_path, ssns_path):
        # Private data setup
        # Expecting one secret key per line
        with open(secretkeys_path, "r") as sk_file:
            self.secretkeys = [
                bytes(key.strip(), encoding="utf-8") for key in sk_file.readlines()
            ]
        # Expecting one ssn per line
        with open(ssns_path, "r") as ssn_file:
            ssns = [ssn.strip() for ssn in ssn_file.readlines()]

        self.secretkey_to_ssn = dict(zip(self.secretkeys, ssns))
        self.ciphertexts = [
            self.encrypt(key, value) for key, value in self.secretkey_to_ssn.items()
        ]

    def encrypt(
        self,
        secret_key: str,
        value: str,
    ) -> str:
        """
        Encrypts SSNs based on secret key

            Args:
                secret_key (str): Secret key
                ssn (str): SSN to encrypt

            Returns:
                (str): Encrypted ciphertext of SSN
        """
        encryptor = pyffx.Integer(secret_key, length=1)
        return "".join([str(encryptor.encrypt(int(digit))) for digit in value])

    def decrypt(
        self,
        secret_key: str,
        ciphertext: str,
    ) -> str:
        """
        Decrypts SSN ciphertexts based on secret key

            Args:
                secret_key (str): Secret key
                ssn_ciphertext (str): Encrypted SSN ciphertext to decrypt

            Returns:
                (str): Original SSN
        """
        encryptor = pyffx.Integer(secret_key, length=1)
        return "".join([str(encryptor.decrypt(int(digit))) for digit in ciphertext])

    def post_process(self, result: str, user_id: int) -> str:
        """
        Postprocesses output from LLM returned after agent execution by looking for any numbers and decrypting them

            Args:
                result (str): Output from LLM
                user_id (int): User ID used to retrieve secret key

            Returns:
                (str): Output from LLM but with numbers replaced by their digit-by-digit decryption
        """
        nums = re.findall(r"\d+", result)
        for num in nums:
            # Decrypt using user's secret key
            result = result.replace(num, self.decrypt(self.secretkeys[user_id], num))
        return result

    def get_number(self, user_id: int) -> str:
        """Gets the encrypted ciphertext of the user's SSN"""
        return self.ciphertexts[user_id]


class LlamaSSNAgent(SSNAgent):
    def __init__(self, secretkeys_path, ssns_path, model_name):
        super().__init__(secretkeys_path, ssns_path)
        self.model_name = model_name

    def run_agent(self, user_query: str, user_id: int) -> str:
        """
        Runs an agent using Llama2 as the LLM

            Args:
                user_query (str): User input to respond to
                user_id (int): User ID used to retrieve SSN if agent deems it necessary

            Returns:
                (str): Response generated by agent
        """
        # Decide on what tool to use
        tool_selector_chain = create_tool_selection_chain()
        tool = tool_selector_chain.invoke({"input": user_query})
        print("Selected tool: " + tool)
        # Make sure that the correct tool is picked
        if tool != "get_number":
            sys.exit("Wrong tool")
        else:
            ciphertext = self.get_number(user_id)
        # Fulfill user request
        request_handling_chain = create_request_handling_chain()
        result = request_handling_chain.invoke(
            {"input": user_query, "ciphertext": ciphertext}
        )
        print("Initial agent output: " + result)
        return result


class OpenAISSNAgent(SSNAgent):
    def __init__(self, secretkeys_path, ssns_path, model_name):
        super().__init__(secretkeys_path, ssns_path)
        self.model_name = model_name

        # Tool creation
        class ReturnNumberInput(BaseModel):
            user_id: int = Field(description="user id number")

        # Tool for returning SSN ciphertext to agent
        self.return_number = StructuredTool.from_function(
            func=self.get_number,
            name="return_number",
            description="""Gets randomly-generated numbers""",
            args_schema=ReturnNumberInput,
        )

        class DummyToolInput(BaseModel):
            x: int = Field(description="number")

        self.dummy_tool = StructuredTool.from_function(
            func=lambda x: x,
            name="dummy_tool",
            description="""Dummy tool, doesn't do anything""",
            args_schema=DummyToolInput,
        )

        class AddNumbersInput(BaseModel):
            x: int = Field(description="First number to add")
            y: int = Field(description="Second number to add")

        self.add_numbers = StructuredTool.from_function(
            func=lambda x, y: x + y,
            name="add_numbers",
            description="""Adds two numbers together and returns the result""",
            args_schema=AddNumbersInput,
        )

    def create_agent(self, model_name: str = "gpt-3.5-turbo") -> Runnable:
        """
        Creates an agent runnable with access to the tools return_number,
        dummy_tool, and add_numbers.

            Args:
                model_name (str): OpenAI LLM name for agent reasoning

            Returns:
                (Runnable): Langchain runnable representing agent
        """
        # Need to set OPENAI_API_KEY environment variable: export OPENAI_API_KEY="<key>"
        llm = ChatOpenAI(model=model_name, temperature=0)
        llm_with_tools = llm.bind_tools(
            [self.return_number, self.dummy_tool, self.add_numbers]
        )

        template_query = """Based on the user id below, return a response to the user's question:
        User ID: {user_id}
        Question: {question}
        """
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a lab assistant that returns made-up numbers to lab workers.",
                ),
                ("human", template_query),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = (
            {
                "question": lambda x: x["question"],
                "user_id": lambda x: x["user_id"],
                "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                    x["intermediate_steps"]
                ),
            }
            | prompt_template
            | llm_with_tools
            | OpenAIToolsAgentOutputParser()
        )
        return agent

    def run_agent(self, user_query: str, user_id: int) -> str:
        """
        Runs an agent using gpt-3.5-turbo as the LLM

            Args:
                user_query (str): User input to respond to
                user_id (int): User ID used to retrieve SSN if agent deems it necessary

            Returns:
                (str): Response generated by agent
        """
        agent_executor = AgentExecutor(
            agent=self.create_agent(),
            tools=[self.return_number, self.dummy_tool, self.add_numbers],
            verbose=True,
        )
        result = agent_executor.invoke({"question": user_query, "user_id": user_id})
        return result["output"]


def main(args):
    agents = {
        "gpt-3.5-turbo": OpenAISSNAgent,
        "gpt-4-turbo": OpenAISSNAgent,
        "llama2": LlamaSSNAgent,
    }

    # User prompt
    user_query = input("What would you like to do today?\n>>> ")
    # Run agent
    # User ID correlates to the index of the secret key in secretkeys, not really a user ID in essence
    agent = agents[args.model](args.secretkeys_path, args.ssns_path, args.model)
    result = agent.run_agent(user_query, args.user_id)
    # Decrypt ciphertext
    post_processed_result = agent.post_process(result, args.user_id)
    print("Postprocessed output: " + post_processed_result)
    print(
        "Original SSN for comparison: "
        + agent.secretkey_to_ssn[agent.secretkeys[args.user_id]]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["gpt-3.5-turbo", "gpt-4-turbo", "llama2"],
        default="gpt-3.5-turbo",
        help="LLM for agent reasoning",
    )
    parser.add_argument(
        "--user_id",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
        help="Index of SSN to use",
    )
    parser.add_argument("--ssns_path", default="ssns.txt", help="Path to ssns")
    parser.add_argument(
        "--secretkeys_path", default="secretkeys.txt", help="Path to secret keys"
    )

    args = parser.parse_args()
    main(args)
