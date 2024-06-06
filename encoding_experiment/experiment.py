import argparse
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from random import randrange, seed
import json
import time
import datetime

from encoding_experiment.encoder import Encoder


def create_chain(model: str):
    """Creates chain to interface with LLM for experiment."""
    llm = ChatOpenAI(model=model, temperature=0)
    query_template = """
    You are an assistant that responds to user questions. You know that slicing
    a string involves getting the characters in the specified locations. Here
    are some examples:
    First three characters of hello: hel
    Last three characters of hello: llo
    
    Answer the question without preamble.

    Question: {question}

    Response:
    """
    prompt = ChatPromptTemplate.from_template(query_template)
    return {"question": lambda x: x["question"]} | prompt | llm | StrOutputParser()


def generate_random_string(encoder: Encoder):
    """
    Generates a random string of random size composed of only characters in
    the encoder's alphabet.
    """
    # Size of random string between 2 and 40
    # 2 so that slicing can be performed (if len == 1 it's just returning s)
    # 40 is arbitrary
    s_len = randrange(2, 40)
    # Random character in encoder's alphabet
    return "".join(
        [
            encoder.encoding[randrange(0, len(encoder.encoding))]
            for _ in range(s_len + 1)
        ]
    )


def main(args):
    seed(args.seed)
    # Set of already tested strings as a safeguard to not test duplicate strings
    tested = {""}
    success_cases = {}
    failure_cases = {}
    area = {0: "first", 1: "last"}
    chain = create_chain(args.model)
    encoder = Encoder()
    s = ""

    i = 1
    while i <= args.num_trials:
        print(f"Trial {i} at time {datetime.datetime.now()}")
        while s in tested:
            s = generate_random_string(encoder)
        tested.add(s)
        encoded_s = encoder.encode(s)
        slice_length = randrange(1, len(s))
        location = randrange(0, 2)
        question = (
            f"What are the {area[location]} {slice_length} characters of {encoded_s}"
        )
        # Code expects LLM to return just the slice we ask it for without preamble.
        # If there is an error with the response format, try the same query again.
        while True:
            try:
                result = chain.invoke({"question": question})
                print(question)
                print(result)
                decoded_result = encoder.encode(result)
                # Check result
                if location == 0 and decoded_result == s[:slice_length]:
                    success_cases[question] = result
                elif location == 1 and decoded_result == s[-slice_length:]:
                    success_cases[question] = result
                else:  # LLM result is wrong
                    failure_cases[question] = result
                i += 1
                break
            except Exception as e:
                print(e)
                time.sleep(5)  # Don't send requests too fast
        time.sleep(5)  # Don't send requests too fast

    print(f"Success rate: {len(success_cases) / args.num_trials * 100}%")

    # Write logs (question and LLM result)
    if args.success_log is not None:
        with open(args.success_log, "w") as f:
            f.write(json.dumps(success_cases, indent=4))
    if args.failure_log is not None:
        with open(args.failure_log, "w") as f:
            f.write(json.dumps(failure_cases, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["gpt-3.5-turbo", "gpt-4-turbo"],
        default="gpt-3.5-turbo",
        help="LLM for agent reasoning",
    )
    parser.add_argument(
        "--num_trials", type=int, default=10000, help="Number of trials for experiment"
    )
    parser.add_argument(
        "--success_log", default=None, help="File to write successful trials to"
    )
    parser.add_argument(
        "--failure_log", default=None, help="File to write unsuccessful trials to"
    )
    parser.add_argument("--seed", type=int, default=9172)
    args = parser.parse_args()

    main(args)
