import fire
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from random import randrange

from encoding import encode

def create_chain():
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    prompt_template = ChatPromptTemplate.from_messages(
        (
            "system",
            """
                You are an assistant that responds to user queries. Return your response to the query without any preamble.
            """
         ),
         ("human", {input})
    )
    return {"input": lambda x: x["input"]} | prompt_template | llm | StrOutputParser()

def main():
    chain = create_chain()
    queries = {
        "What are the first three characters of ": lambda x: x[:3],
        "What are the last four characters of ": lambda x: x[-4:],
        "What is the first character of ": lambda x: x[0],
        "What is the last character of ": lambda x: x[-1],
    }
    words = []
    num_success = 0
    for word in words:
        query = list(queries.keys())[randrange(0, len(queries))]
        llm_response = chain.invoke({"input": query + word})
        if queries[query](word) == llm_response:
            num_success += 1

    print(f"Success rate: {num_success / len(words)}")
        

if __name__ == "__main__":
    main()