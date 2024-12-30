# test communication to Feishu

import time
import datetime
import hashlib
import base64
import hmac
import requests
from requests_toolbelt import MultipartEncoder
import logging
import json

import lark_oapi as lark
from dotenv import load_dotenv
import os
from lark_oapi.api.im.v1 import (
    CreateImageRequest, CreateImageRequestBody, CreateImageResponse,
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

if __name__ == '__main__':
    
    # Webhook:
    load_dotenv()

    webhook_url = os.getenv('GROUP_WEBHOOK_URL')
    webhook_secret = os.getenv('GROUP_WEBHOOK_SECRET')

    if 0:
        # Send message
        group_bot_send_msg("text", "Hello, Kiwi!", webhook_url, webhook_secret)

    app_id = os.getenv('APP_ID')
    app_secret = os.getenv('APP_SECRET')

    if 0:
        # Upload image
        img_path = 'test_bot.webp'

        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()

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

# Ref.
# https://open.feishu.cn/document/home/develop-a-bot-in-5-minutes/step-5-configure-event-subscription