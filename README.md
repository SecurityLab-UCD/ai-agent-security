# ai-agent-security
This repository contains source code for the demos and attacks we present in our paper.

## Requirements
[Python 3.8](https://www.python.org/downloads/release/python-380/) or above

## Setup
`env.sh` is for letting Python find our modules. Source it from repo root directory.  
```sh
source ./src/env.sh
```

Run `init.sh` to install dependencies
```sh
./src/init.sh
```

Generate homomorphic encryption data
- Run `python HE_data.py -h` to see how to modify generated ciphertexts
```sh
cd HE_data && python HE_data.py && cd ../
```

## Run Demos
To run agents using OpenAI LLMs for reasoning, set this environment variable first
```sh
export OPENAI_API_KEY="<key>"
```

### SSN Agent Demo
To run the agent
```sh
python agents/ssn_agent.py --agent="<agent>" --user_id=<id>
```

When prompting, write "number" instead of "SSN" or "social security number" to avoid triggering alignment. You can ask for groups of the number such as the first three digits or last four digits.

Example prompt: `What are the first three digits of my number?`

### Homomorphic Encryption Agent Demo
To run the agent
```sh
python agents/HE_agent.py
```
When prompting, please specify "sum" or "product" for postprocessing reasons. The default encryptor we use cannot handle numbers greater than 400 (this can be changed in `HE_data/HE_data.py`), so limit calculation results to the range 0 to 400 inclusive.

Example prompt: `What is the product of indices 0 and 1?`
- Known bug: The LLM indexes the wrong thing if 0 is not included as an index in the prompt. Make sure the first index you write in the prompt is 0.

## Tests
To run tests
```sh
# Create ciphertext files
cd HE_data && python HE_data.py && cd ../

# Run tests
pytest tests/*
```