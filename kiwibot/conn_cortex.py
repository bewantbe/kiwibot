# use LLM to give response

import os
import copy
import time
import json
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic

def GetTimeStamp():
    """return like '2025-01-14T07:03:43.273'"""
    t = time.time()
    ms = int((t - int(t)) * 1000)
    return time.strftime('%Y-%m-%dT%H:%M:%S.', time.localtime(t)) + f"{ms:03d}"

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

        self.chat_history = self._get_historical_msg()

    def _get_historical_msg(self):
        # load historical chats from log.json
        s = '[' + open('log.json', encoding='utf-8').read()
        s = s.replace('}\n{', '},\n{') + ']'
        print(s[0:1000])
        print(s[-500:])
        chat_history_all = json.loads(s)
        
        # group messages by chat_id
        chat_history = {}
        for msg in chat_history_all:
            chat_id = msg['chat_id']
            if chat_id not in chat_history:
                chat_history[chat_id] = []
            chat_history[chat_id].append(msg)

        # TODO: if user explicitly asks to start a new chat, clear the chat history

        # print number of messages in each chat
        for chat_id, msgs in chat_history.items():
            print(f"Chat {chat_id} has {len(msgs)} messages.")

        return chat_history

    def deal_message(self, msg_json):
        response = {
            'chat_type': msg_json['chat_type'],
            'chat_id': msg_json['chat_id'],
            'sender_id': self.name,
            'message_type': 'text',
            'message_id': None,
            'content': {
                'text': None
            }
        }
        msg = msg_json['content']['text']

        # load recent history
        chat_id = msg_json['chat_id']
        if chat_id in self.chat_history:
            history = self.chat_history[chat_id][-3:]
        else:
            history = []

        # add recent messages to the history
        messages = [("system", "You are a helpful assistant.")]
        for past_msg in history:
            if past_msg['sender_id'] == self.name:
                messages.append(("ai", past_msg['content']['text']))
            else:
                messages.append(("human", past_msg['content']['text']))

        messages.append(("human", msg))
        ai_msg = self.llm.invoke(messages)
        response['content']['text'] = ai_msg.content
        response['timestamp'] = GetTimeStamp()
        response['update_time'] = response['timestamp']
        return response
    
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
