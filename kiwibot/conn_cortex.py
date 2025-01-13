# use LLM to give response

import os
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic

class MessageDealer:
    """dealing with messages, like cortex in brain"""

    name = 'Kiwi'

    def __init__(self, anthropic_api_key):
        # model list: 
        # param: https://api.python.langchain.com/en/latest/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html
        # basic usages: https://python.langchain.com/docs/integrations/chat/anthropic/
        # claude-3-5-haiku-latest, claude-3-5-sonnet-latest, claude-3-5-sonnet-20241022
        self.llm = ChatAnthropic(model="claude-3-5-sonnet-latest",
                                 api_key=anthropic_api_key)

        # load historical chats

    def deal_message(self, msg):
        messages = [
            ("system", "You are a helpful assistant."),
            ("human", msg)
        ]
        ai_msg = self.llm.invoke(messages)
        return ai_msg.content
    
    def __call__(self, *args, **kwds):
        return self.deal_message(*args, **kwds)

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
