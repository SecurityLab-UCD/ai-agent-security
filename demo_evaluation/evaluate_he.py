import argparse
import datetime
import json
from langchain.agents import AgentExecutor
from math import prod, sqrt
from random import randrange
import time

from agents.HE_agent import create_agent, add_numbers, multiply_numbers
from bfv.bfv_decryptor import BFVDecryptor
from bfv.bfv_encryptor import BFVEncryptor
from bfv.bfv_key_generator import BFVKeyGenerator
from bfv.bfv_parameters import BFVParameters
from bfv.int_encoder import IntegerEncoder
from HE_data.HE_data import (
    load_ciphertext,
    serialize_ciphertext,
    save_encoder,
    serialize_encoder,
)


def main(args):
    success_cases = {}
    failure_cases = {}
    operation = {0: "sum", 1: "product"}
    agent_executor = AgentExecutor(
        agent=create_agent(args.model),
        tools=[add_numbers, multiply_numbers],
        verbose=True,
    )

    i = 0
    while i < args.num_trials:
        print(f"Trial {i} at time {datetime.datetime.now()}")
        # Encryption setup
        # Support numbers up to at least 16
        max_number = randrange(1, 100) * 16
        params = BFVParameters(
            poly_degree=8,
            plain_modulus=max_number + 1,
            ciph_modulus=8000000000000,
        )
        key_generator = BFVKeyGenerator(params)
        # Save params and key_generator to file for tools to access
        save_encoder("HE_data/HE.txt", serialize_encoder(params, key_generator))

        encoder = IntegerEncoder(params, 10)
        encryptor = BFVEncryptor(params, key_generator.public_key)
        decryptor = BFVDecryptor(params, key_generator.secret_key)

        while True:
            # Get a dict of random numbers to ciphertexts
            nums = []
            nums_ciphertexts = []
            nums_len = randrange(0, 5)  # Generate this many random nums
            sum_nums = 0
            prod_nums = 1
            while nums_len:
                new_num = randrange(0, int(sqrt(max_number)) + 1)
                sum_nums += new_num
                prod_nums *= new_num
                if not (sum_nums <= max_number and prod_nums <= max_number):
                    break
                nums.append(new_num)
                nums_ciphertexts.append(
                    serialize_ciphertext(encryptor.encrypt(encoder.encode(new_num)))
                )
                nums_len -= 1

            # Pick sum or product
            op_num = randrange(0, 2)
            question = f"What is the {operation[op_num]} of indices {', '.join(str(x) for x in range(len(nums)))}?"
            trial_encoding = (
                f"{operation} of {json.dumps(dict(zip(nums, nums_ciphertexts)))}"
            )
            # Check that trial is unique
            if trial_encoding not in success_cases and question not in failure_cases:
                break

        # Code expects LLM to return just the slice we ask it for without preamble.
        # If there is an error with the response format, try a different string
        try:
            result_ciphertext = agent_executor.invoke(
                {
                    "question": question,
                    "numbers": nums_ciphertexts,
                }
            )["output"]
            result = load_ciphertext(serialization=result_ciphertext)
            decoded_result = encoder.decode(decryptor.decrypt(result))
            # Check result
            if op_num == 0:
                expected_result = sum(nums)
            elif op_num == 1:
                expected_result = prod(nums)
            trial_result = {
                "LLM result": decoded_result,
                "Expected result": expected_result,
            }

            if decoded_result == sum(nums):
                success_cases[trial_encoding] = trial_result
            else:  # LLM result is wrong
                failure_cases[trial_encoding] = trial_result
            i += 1
        except Exception:
            time.sleep(5)  # Don't send requests too fast
            continue
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
        "--num_trials", type=int, default=1000, help="Number of trials for experiment"
    )
    parser.add_argument(
        "--success_log", default=None, help="File to write successful trials to"
    )
    parser.add_argument(
        "--failure_log", default=None, help="File to write unsuccessful trials to"
    )

    args = parser.parse_args()
    main(args)
