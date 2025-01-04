# use LLM to give response

import os
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic

# Ref. Build a Chatbot - LangChain
# https://python.langchain.com/docs/tutorials/chatbot/
# Ref. Build an Agent
# https://python.langchain.com/docs/tutorials/agents/
# Ref. Build a Retrieval Augmented Generation (RAG) App: Part 1
# https://python.langchain.com/docs/tutorials/rag/

# To ask questions
# https://chat.langchain.com/

if __name__ == '__main__':
    # test only
    load_dotenv()

    # Instantiate the ChatAnthropic model
    llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")

    # Define a function to interact with the chatbot
    def chat_with_bot(user_input):
        messages = [
            ("system", "You are a helpful assistant."),
            ("human", user_input)
        ]
        ai_msg = llm.invoke(messages)
        return ai_msg.content

    # Example interaction
    user_input = "Where to find MH370?"
    response = chat_with_bot(user_input)
    print("Bot:", response)
