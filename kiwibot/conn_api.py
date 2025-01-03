# interface for communication
# so far mostly Feishu

import os
import time
from datetime import datetime
import hashlib
import base64
import hmac
import logging
import json

import threading
import queue

import requests
from requests_toolbelt import MultipartEncoder

from dotenv import load_dotenv
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateImageRequest, CreateImageRequestBody, CreateImageResponse,
    CreateMessageRequest, CreateMessageRequestBody, CreateMessageResponse,
    ReplyMessageRequest, ReplyMessageRequestBody, ReplyMessageResponse,
    P2ImMessageReceiveV1,
)


# setup logging
logging.basicConfig(level=logging.INFO)

def group_bot_gen_sign(timestamp, secret):
    # Splicing timestamp and secret
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    # Perform base64 processing on the result
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

def group_bot_send_msg(msg_type, content, webhook_url, webhook_secret):
    logging.info('Sending message...')
    timestamp = int(time.time())

    if msg_type == "text" and isinstance(content, str):
        content = {
            "text": content
        }

    req_msg = {
        "timestamp": str(timestamp),
        "sign": group_bot_gen_sign(timestamp, webhook_secret),
        "msg_type": msg_type,
        "content": content
    }

    # Send POST request
    response = requests.post(webhook_url, json=req_msg)
    logging.info("Response:")
    logging.info(response.status_code)
    logging.info(response.json())

def upload_img(img_path, client):
    # 构造请求对象
    request: CreateImageRequest = CreateImageRequest.builder() \
        .request_body(CreateImageRequestBody.builder()
            .image_type("message")
            .image(open(img_path, 'rb'))
            .build()) \
        .build()

    # 发起请求
    response: CreateImageResponse = client.im.v1.image.create(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f'client.im.v1.image.create failed, code: {response.code},'
            f'msg: {response.msg}, log_id: {response.get_log_id()},'
            f'resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}'
        )
        return

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))
    return response.data


def get_tenant_access_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    response = requests.request("POST", url, json=payload, headers=headers)
    r = response.json()
    # in r['tenant_access_token']
    return r

def send_msg_to_user(user_id_in_app, msg_type, content, client):
    # Ref. https://open.feishu.cn/document/server-docs/im-v1/message/create

    if msg_type == "text" and isinstance(content, str):
        content = {
            "text": content
        }

    request: CreateMessageRequest = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(CreateMessageRequestBody.builder()
            .receive_id(user_id_in_app)
            .msg_type(msg_type)
            .content(json.dumps(content, ensure_ascii=False))
            .build()) \
        .build()

    # 发起请求
    response: CreateMessageResponse = client.im.v1.message.create(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.im.v1.message.create failed, code: {response.code}, "
            f"msg: {response.msg}, log_id: {response.get_log_id()}, "
            f"resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}"
        )
        return

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))

# Register event handler to handle received messages.
# https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive
def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1, client) -> None:
    res_content = ""
    if data.event.message.message_type == "text":
        res_content = json.loads(data.event.message.content)["text"]
    else:
        res_content = "Failed to parse, please send text message"

    content = json.dumps(
        {
            "text": "Received message:"\
                   + res_content
        }
    )

    if data.event.message.chat_type == "p2p":
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(data.event.message.chat_id)
                .msg_type("text")
                .content(content)
                .build()
            )
            .build()
        )
        # Use send OpenAPI to send messages
        # https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
        response = client.im.v1.chat.create(request)

        if not response.success():
            raise Exception(
                f"client.im.v1.chat.create failed, code: {response.code}, "
                f"msg: {response.msg}, log_id: {response.get_log_id()}"
            )
    else:
        # replay when @at
        request: ReplyMessageRequest = (
            ReplyMessageRequest.builder()
            .message_id(data.event.message.message_id)
            .request_body(
                ReplyMessageRequestBody.builder()
                .content(content)
                .msg_type("text")
                .build()
            )
            .build()
        )
        # Reply to messages using send OpenAPI
        # https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/reply
        response: ReplyMessageResponse = client.im.v1.message.reply(request)
        if not response.success():
            raise Exception(
                f"client.im.v1.message.reply failed, code: {response.code}, "
                f"msg: {response.msg}, log_id: {response.get_log_id()}"
            )

def start_echo_bot(client):
    # Echo bot
    # Ref. https://open.feishu.cn/document/uAjLw4CM/uMzNwEjLzcDMx4yM3ATM/develop-an-echo-bot/development-steps
    # Ref. https://github.com/larksuite/lark-samples/tree/main/echo_bot/python

    # Register event handler.
    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
        .build()
    )
    wsClient = lark.ws.Client(
        lark.APP_ID,
        lark.APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.DEBUG,
    )

    #  Start long-lived connection and register event handler.
    wsClient.start()

class FeishuPortal:
    def __init__(self, app_id, app_secret, log_file):
        self.lark_log_level = lark.LogLevel.DEBUG
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(self.lark_log_level) \
            .build()
        self.recv_queue = queue.Queue()
        self.send_queue = queue.Queue()
        self.log_file = log_file
        self.lock = threading.Lock()
        self.app_id = app_id
        self.app_secret = app_secret
        self._init_event_handler()
        self._start_sending_thread()

    def _init_event_handler(self):
        event_handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._on_message_received)
            .build()
        )
        self.ws_client = lark.ws.Client(
            self.app_id,
            self.app_secret,
            event_handler=event_handler,
            log_level=self.lark_log_level,
        )
        self._start_ws_client_thread()

    def _start_ws_client_thread(self):
        def start_ws_client():
            self.ws_client.start()  # this is blocking

        thread = threading.Thread(target=start_ws_client)
        thread.daemon = True
        thread.start()

    def _on_message_received(self, data: P2ImMessageReceiveV1):
        msg = self.get_pack_msg(data)
        self.recv_queue.put(msg)
        self._log_communication(msg)

    def send_message(self, msg):
        content = json.dumps(msg['content'])

        if msg['chat_type'] == "p2p":
            request = (
                CreateMessageRequest.builder()
                .receive_id_type("chat_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(msg['chat_id'])
                    .msg_type("text")
                    .content(content)
                    .build()
                )
                .build()
            )
            response = self.client.im.v1.chat.create(request)

            if not response.success():
                raise Exception(
                    f"client.im.v1.chat.create failed, code: {response.code}, "
                    f"msg: {response.msg}, log_id: {response.get_log_id()}"
                )
        else:
            request: ReplyMessageRequest = (
                ReplyMessageRequest.builder()
                .message_id(msg['message_id'])
                .request_body(
                    ReplyMessageRequestBody.builder()
                    .content(content)
                    .msg_type("text")
                    .build()
                )
                .build()
            )
            response: ReplyMessageResponse = self.client.im.v1.message.reply(request)
            if not response.success():
                raise Exception(
                    f"client.im.v1.message.reply failed, code: {response.code}, "
                    f"msg: {response.msg}, log_id: {response.get_log_id()}"
                )

        self._log_communication(msg)

    @staticmethod
    def isotime_from_epoch(epoch):
        return datetime.fromtimestamp(int(epoch)/1000).isoformat(timespec='milliseconds')

    @staticmethod
    def get_pack_msg(payload):
        message = payload.event.message
        return {
            "timestamp": FeishuPortal.isotime_from_epoch(message.create_time),
            "chat_type": message.chat_type,
            "message_type": message.message_type,
            "chat_id": message.chat_id,
            "message_id": message.message_id,
            "sender_id": payload.event.sender.sender_id.open_id,
            "update_time": FeishuPortal.isotime_from_epoch(message.update_time),
            "content": json.loads(message.content)
        }

    def _log_communication(self, message_log):
        with self.lock:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(message_log, indent=4) + '\n')

    def _start_sending_thread(self):
        def send_from_queue():
            while True:
                msg = self.send_queue.get()
                self.send_message(msg)
                self.send_queue.task_done()

        thread = threading.Thread(target=send_from_queue)
        thread.daemon = True
        thread.start()

def old_main():
    load_dotenv()

    webhook_url = os.getenv('GROUP_WEBHOOK_URL')
    webhook_secret = os.getenv('GROUP_WEBHOOK_SECRET')

    # Test send message to group
    if 0:
        group_bot_send_msg("text", "Hello, Kiwi!", webhook_url, webhook_secret)

    app_id = os.getenv('APP_ID')
    app_secret = os.getenv('APP_SECRET')

    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.DEBUG) \
        .build()

    if 0:
        # Upload image
        img_path = 'test_bot.webp'

        r = upload_img(img_path, client)
        print(r)
        image_key = r['image_key']
        print(image_key)
    else:
        image_key = "img_v3_02i2_45d27df1-9978-447f-bd35-a43a7b844c4g"

    if 0:
        # Send message with image
        content = {
            "image_key": image_key
        }
        group_bot_send_msg("image", content, webhook_url, webhook_secret)
    
    if 0:
        # test application bot
        user_id_in_app = 'ou_0b2ada4556de2f7b7ddc6557b6f4292b'
        send_msg_to_user(user_id_in_app, "text", "Hello, this is Kiwi!", client)

    start_echo_bot(client)

if __name__ == '__main__':
    #old_main()
    pass