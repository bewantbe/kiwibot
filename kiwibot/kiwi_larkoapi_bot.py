# test communication to Feishu

import os
import time
from dotenv import load_dotenv
from conn_api import (
    FeishuPortal,
)
from conn_router import MessageRouter
from conn_cortex import MessageDealer

def main_test1():
    load_dotenv()
    print('Start main')

    app_id = os.getenv('APP_ID')
    app_secret = os.getenv('APP_SECRET')
    feishu_portal = FeishuPortal(app_id, app_secret, "log.json")
    while True:
        # get message from feishu_portal.send_queue and send to send_quque
        msg = feishu_portal.recv_queue.get()
        print(msg)
        msg['content']['text'] = f"Received: {msg['content']['text']}"
        feishu_portal.send_queue.put(msg)
        feishu_portal.recv_queue.task_done()
        break
    feishu_portal.send_queue.join()
    time.sleep(1)

def main_test2():
    load_dotenv()
    print('Start main')

    # init feishu
    app_id = os.getenv('APP_ID')
    app_secret = os.getenv('APP_SECRET')
    feishu_portal = FeishuPortal(app_id, app_secret, "log.json")

    # init message router
    msg_router = MessageRouter(feishu_portal.recv_queue, feishu_portal.send_queue)
    
    # init agent
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    msg_dealer = MessageDealer(anthropic_api_key)
    msg_router.set_message_dealer(msg_dealer.deal_message)

    msg_router.start()
    #msg_router.register_timed_event(15, 'eddy', 'time')  # cost extra ctrl-c

    # start message-agent loop
    msg_router.join()

if __name__ == '__main__':
    main_test2()
    # TODO: allow one Ctrl-C to terminate the program