# test communication to Feishu

import os
import time
import datetime
import hashlib
import base64
import hmac
import logging
import json

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
def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
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

if __name__ == '__main__':
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
