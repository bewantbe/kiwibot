# test communication to Feishu

import os
import time
import json
from dotenv import load_dotenv

from kiwibot.conn_lark import (
    FeishuPortal,
    simple_msg_by,
)
from kiwibot.conn_router import MessageRouter
from kiwibot.conn_cortex import MessageDealer

def main_test_echo():
    print('Starting echo bot')
    load_dotenv()
    app_id = os.getenv('APP_ID')
    app_secret = os.getenv('APP_SECRET')
    feishu_portal = FeishuPortal(app_id, app_secret, "log.json")

    msg_router = MessageRouter(feishu_portal.recv_queue, feishu_portal.send_queue)
    msg_router.set_message_dealer(
        lambda m: simple_msg_by(m, 'Kiwi', "Received: " + json.dumps(m)))
    msg_router.start()
    msg_router.join()  # start message-agent loop

def main_ai_assistant():
    print('Starting AI chat bot')
    load_dotenv()

    # init feishu connection
    app_id = os.getenv('APP_ID')
    app_secret = os.getenv('APP_SECRET')
    chat_log_path = 'log.json'
    if not os.path.exists(chat_log_path):
        with open(chat_log_path, 'w') as f:
            pass
    feishu_portal = FeishuPortal(app_id, app_secret, chat_log_path)

    # init message router
    msg_router = MessageRouter(feishu_portal.recv_queue, feishu_portal.send_queue)
    
    # init AI agent
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    msg_dealer = MessageDealer(anthropic_api_key, chat_log_path, 
                               {
                                   'chattool': feishu_portal.chattool,
                               })
    msg_router.set_message_dealer(msg_dealer)

    #msg_router.register_timed_event(15, 'eddy', 'time')  # cost extra ctrl-c

    # start message-agent loop
    msg_router.start()
    msg_router.join()

if __name__ == '__main__':
    #main_test_echo()
    main_ai_assistant()
    # TODO: allow one Ctrl-C to terminate the program