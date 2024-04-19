# ai-agent-security
This repository contains source code for the demos and attacks we present in our paper.

## Setup
Install requirements
```sh
pip install -r requirements.txt
```
`env.sh` is for letting Python find our modules. Source it from repo root directory.  
```sh
source ./src/env.sh
```

Generate homomorphic encryption data
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
`agent` can be either `llama2` or `gpt-3.5-turbo` (default `gpt-3.5-turbo`)

`id` can be any integer between 0 and 3 inclusive (default 0)
- We provide four numbers in an array to test the agent on

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
pytest tests/*
```