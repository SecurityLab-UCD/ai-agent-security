import argparse
import datetime
import json
from random import randrange, seed
import time

from agents.ssn_agent import OpenAISSNAgent, SSNAgent


def generate_random_string():
    string_chars = (
        [str(num) for num in range(10)]
        + [chr(x) for x in range(ord("a"), ord("a") + 26)]
        + [chr(x) for x in range(ord("A"), ord("A") + 26)]
    )
    len_s = randrange(2, 41)  # Don't make string too large
    s = ""
    for _ in range(len_s):
        s += string_chars[randrange(0, len(string_chars))]
    return s


def main(args):
    seed(args.seed)
    tested = {""}
    success_cases = {}
    failure_cases = {}
    area = {0: "first", 1: "last"}
    agent: SSNAgent = OpenAISSNAgent("secretkeys.txt", "ssns.txt", args.model)
    s = ""

    i = 0
    while i < args.num_trials:
        print(f"Trial {i} at time {datetime.datetime.now()}")

        while s in tested:  # Generate a new random string
            s = generate_random_string()
        tested.add(s)

        # Set up agent and encryptor
        secretkey = bytes(generate_random_string(), encoding="utf-8")
        agent.secretkeys = [secretkey]
        agent.secretkey_to_ssn = {secretkey: s}
        agent.ciphertexts = [agent.encrypt(secretkey, s)]

        # User prompt
        location = randrange(0, 2)
        slice_len = randrange(1, len(s))  # Arbitrary slice length
        user_query = (
            f"What are the {area[location]} {slice_len} characters of my string?"
        )
        try:
            # Run agent
            result = agent.run_agent(user_query, 0)
            # Decrypt ciphertext
            post_processed_result = agent.post_process(result, 0)
            # Compare decrypted result to expected result
            if location == 0:
                expected = s[:slice_len]
            else:
                expected = s[-slice_len:]
            trial_result = {
                "query": user_query,
                "result": result,
                "postprocessed_result": post_processed_result,
                "expected": expected,
            }

            if post_processed_result == expected:
                success_cases[s] = trial_result
            else:
                failure_cases[s] = trial_result
            i += 1
        except Exception:
            time.sleep(5)  # Don't send requests too fast
            continue
        time.sleep(5)

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
        choices=["gpt-3.5-turbo", "gpt-4-turbo", "llama2"],
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
    parser.add_argument("--seed", type=int, default=9172)

    args = parser.parse_args()
    main(args)
