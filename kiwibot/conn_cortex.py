# use LLM to give response

import os
import copy
import time
import json

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
#from langchain_anthropic import ChatAnthropic

from kiwibot.utils import (
    GetISOTimestamp,
)
from kiwibot.conn_lark import (
    simple_msg_by,
    is_at_user,
)

class MessageDealer:
    """dealing with messages, like the cortex in brain"""

    name = 'Kiwi'   # name will appear in message log

    def __init__(self, chat_database_path, tool_dict=None):
        """Init connection to Anthropic, load historical messages"""
        load_dotenv()
        # param: https://api.python.langchain.com/en/latest/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html
        # basic usages: https://python.langchain.com/docs/integrations/chat/anthropic/
        # model list:
        # gpt-3.5-turbo, deepseek-r1:70b, deepseek-r1:32b
        self.llm = ChatOpenAI(model_name     = os.getenv("OPENAI_MODEL_NAME"),
                              base_url       = os.getenv('OPENAI_API_URL'),
                              openai_api_key = os.getenv('OPENAI_API_KEY'))
        # model list: 
        # claude-3-5-haiku-latest, claude-3-5-sonnet-latest, claude-3-5-sonnet-20241022
        #anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        #self.llm = ChatAnthropic(model="claude-3-5-sonnet-latest",
        #                         api_key=anthropic_api_key)

        self.tool_dict = tool_dict
        self.chat_database_path = chat_database_path
        self.chat_history = self._get_historical_msg(chat_database_path)

    def _get_historical_msg(self, chat_database_path):
        """ load historical chats from database """
        if chat_database_path is None:
            return {}

        s = open(chat_database_path, encoding='utf-8').read()
        s = '[' + s.replace('}\n{', '},\n{') + ']'
        chat_history_all = json.loads(s)
        
        # group messages by chat_id
        chat_history = {}
        for msg in chat_history_all:
            chat_id = msg['chat_id']
            if chat_id not in chat_history:
                chat_history[chat_id] = []
            chat_history[chat_id].append(msg)

        # print number of messages in each chat
        for chat_id, msgs in chat_history.items():
            print(f"Chat {chat_id} has {len(msgs)} messages.")

        return chat_history

    def is_need_to_reply(self, msg_json):
        # if it is from user chat, reply it
        if msg_json['chat_type'] == 'p2p':
            return True
        # if it is from group chat, reply it only when @me
        if msg_json['chat_type'] == 'group':
            return is_at_user(msg_json, self.name)

    def gen_prompt(self, msg_json):
        if self.tool_dict is None:
            return ''
        if msg_json['chat_type'] == 'p2p':
            user_name = self.tool_dict['chattool'].get_user_name(msg_json['sender_id'])
            return f"You are chatting with {user_name}."
        if msg_json['chat_type'] == 'group':
            group_name = self.tool_dict['chattool'].get_group_name(msg_json['chat_id'])
            return f"You are chatting in a group chat named {group_name}."

    def append_to_history(self, msg_json):
        chat_id = msg_json['chat_id']
        if chat_id not in self.chat_history:
            self.chat_history[chat_id] = []
        self.chat_history[chat_id].append(msg_json)
        # somewhere else will talk case of the history file

    def get_history_content(self, msg_json, max_num=3):
        # load recent history
        chat_id = msg_json['chat_id']
        if chat_id in self.chat_history:
            history = self.chat_history[chat_id][-3:]
        else:
            history = []

        # TODO: if user explicitly asks to start a new chat, clear the chat history
        return history

    def deal_message(self, msg_json):
        """deal with the message, return response"""
        if not self.is_need_to_reply(msg_json):
            self.append_to_history(msg_json)
            return None

        # system prompt
        messages = [("system",
            f"You are a helpful assistant, nicknamed: {self.name}." + \
            " " + self.gen_prompt(msg_json) + \
            " " + f"local time is {time.ctime()}."
            )]

        conv = self.tool_dict['chattool'].get_plain_msg_text

        # add context
        history = self.get_history_content(msg_json)
        for past_msg in history:
            if past_msg['sender_id'] == self.name:
                messages.append(("ai", conv(past_msg)))
            else:
                messages.append(("human", conv(past_msg)))    # TODO: support rich text, image etc.

        msg = conv(msg_json)
        messages.append(("human", msg))
        ai_msg = self.llm.invoke(messages)
        response = simple_msg_by(msg_json, self.name, ai_msg.content)
        self.append_to_history(msg_json)
        self.append_to_history(response)
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

def test_request_response():
    """Test the openai api through raw requests directly"""
    import requests
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # API endpoint
    api_endpoint = "http://10.1.1.5:18434/v1/chat/completions"
    
    # Test message
    messages = [
        {"role": "user", "content": "What is 2+2?"}
    ]
    
    # Request headers and data
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'dummy-key')}"
    }
    
    data = {
        "model": "deepseek-r1:70b",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 150
    }
    
    try:
        response = requests.post(api_endpoint, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        print("Status Code:", response.status_code)
        print("Response:", result)
        return result
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None

if __name__ == '__main__':
    """ main for test only """
    #test_request_response()
    #exit(0)

    load_dotenv()

    # Instantiate the ChatOpenAI model with custom API endpoint
    # set api_key in .env
    llm = ChatOpenAI(
        model_name="deepseek-r1:70b",
        base_url=os.getenv('OPENAI_API_URL')
    )

    # Define a function to interact with the chatbot
    def chat_with_bot(user_input):
        #messages = [
        #    ("system", "You are a helpful assistant."),
        #    ("human", user_input)
        #]
        messages = [
            ("human", user_input),
        ]
        ai_msg = llm.invoke(messages)
        return ai_msg.content

    # Example interaction
    user_input = "Where to find MH370?"
    response = chat_with_bot(user_input)
    print("Bot:", response)
