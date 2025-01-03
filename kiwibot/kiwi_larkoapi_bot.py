# test communication to Feishu

import os
import time
from dotenv import load_dotenv
from conn_api import (
    FeishuPortal,
)

def main():
    load_dotenv()
    print('Start main')

    app_id = os.getenv('APP_ID')
    app_secret = os.getenv('APP_SECRET')
    feishu_portal = FeishuPortal(app_id, app_secret, "log.json")
    while True:
        # get message from feishu_portal.send_queue and send to send_quque
        print('=======================0')
        msg = feishu_portal.recv_queue.get()
        print('=======================1')
        print(msg)
        msg['content']['text'] = f"Received: {msg['content']['text']}"
        feishu_portal.send_queue.put(msg)
        feishu_portal.recv_queue.task_done()
        break
    feishu_portal.send_queue.join()
    time.sleep(1)

if __name__ == '__main__':
    main()