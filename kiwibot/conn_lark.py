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

# ref https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview
class FeishuBase:
    """Interface for Feishu Base API operations"""
    
    def __init__(self, client):
        """Initialize with a lark client instance"""
        self.client = client
        self.base_url = "https://open.feishu.cn/open-apis/bitable/v1"
    
    # Error handling and request methods
    def _handle_error_response(self, response):
        """Handle error responses from the API"""
        if response.get('code') != 0:  # Feishu API uses code 0 for success
            error_msg = response.get('msg', 'Unknown error')
            error_code = response.get('code')
            logging.error(f"API Error {error_code}: {error_msg}")
            raise Exception(f"API Error {error_code}: {error_msg}")
        return response

    def _make_request(self, method, endpoint, params=None, json_data=None):
        """Make HTTP request to Feishu Base API with improved error handling"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.client.tenant_access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data
            )
            response.raise_for_status()
            return self._handle_error_response(response.json())
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'json'):
                try:
                    error_data = e.response.json()
                    logging.error(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    pass
            raise
    
    # App level operations
    def get_app_info(self, app_token):
        """Get Base app information"""
        return self._make_request('GET', f'/apps/{app_token}')

    def update_app_info(self, app_token, name=None, description=None):
        """Update Base app information"""
        data = {}
        if name:
            data['name'] = name
        if description:
            data['description'] = description
        return self._make_request('PUT', f'/apps/{app_token}', json_data=data)

    # Table operations
    def list_tables(self, app_token, page_size=100, page_token=None):
        """List all tables in a Base app"""
        params = {'page_size': page_size}
        if page_token:
            params['page_token'] = page_token
        return self._make_request('GET', f'/apps/{app_token}/tables', params=params)

    def create_table(self, app_token, name, description=None, fields=None):
        """Create a new table in Base app"""
        data = {'name': name}
        if description:
            data['description'] = description
        if fields:
            data['fields'] = fields
        return self._make_request('POST', f'/apps/{app_token}/tables', json_data=data)

    def delete_table(self, app_token, table_id):
        """Delete a table from Base app"""
        return self._make_request('DELETE', f'/apps/{app_token}/tables/{table_id}')

    # Record operations
    def list_records(self, app_token, table_id, view_id=None, page_size=100, page_token=None):
        """List records in a table"""
        params = {'page_size': page_size}
        if view_id:
            params['view_id'] = view_id
        if page_token:
            params['page_token'] = page_token
        return self._make_request('GET', f'/apps/{app_token}/tables/{table_id}/records', params=params)

    def create_record(self, app_token, table_id, fields):
        """Create a new record in a table"""
        data = {'fields': fields}
        return self._make_request('POST', f'/apps/{app_token}/tables/{table_id}/records', json_data=data)

    def update_record(self, app_token, table_id, record_id, fields):
        """Update an existing record"""
        data = {'fields': fields}
        return self._make_request('PUT', f'/apps/{app_token}/tables/{table_id}/records/{record_id}', json_data=data)

    def delete_record(self, app_token, table_id, record_id):
        """Delete a record from a table"""
        return self._make_request('DELETE', f'/apps/{app_token}/tables/{table_id}/records/{record_id}')

    def batch_create_records(self, app_token, table_id, records):
        """Create multiple records in a table"""
        data = {'records': records}
        return self._make_request('POST', f'/apps/{app_token}/tables/{table_id}/records/batch_create', json_data=data)

    def batch_update_records(self, app_token, table_id, records):
        """Update multiple records in a table"""
        data = {'records': records}
        return self._make_request('POST', f'/apps/{app_token}/tables/{table_id}/records/batch_update', json_data=data)

    def batch_delete_records(self, app_token, table_id, record_ids):
        """Delete multiple records from a table"""
        data = {'records': [{'record_id': rid} for rid in record_ids]}
        return self._make_request('POST', f'/apps/{app_token}/tables/{table_id}/records/batch_delete', json_data=data)

    def search_records(self, app_token, table_id, filter_exp=None, sort=None, view_id=None, page_size=100, page_token=None):
        """Search records with filtering and sorting
        
        Args:
            app_token: Base app token
            table_id: Table ID
            filter_exp: Filter expression following Feishu Base filter syntax
            sort: List of fields to sort by, each item being a dict with 'field_name' and 'order' ('asc' or 'desc')
            view_id: Optional view ID to filter records
            page_size: Number of records per page
            page_token: Token for pagination
        """
        params = {'page_size': page_size}
        if view_id:
            params['view_id'] = view_id
        if page_token:
            params['page_token'] = page_token
        if filter_exp:
            params['filter'] = filter_exp
        if sort:
            params['sort'] = json.dumps(sort)
        return self._make_request('GET', f'/apps/{app_token}/tables/{table_id}/records', params=params)

    # Dashboard operations
    def list_dashboards(self, app_token, page_size=100, page_token=None):
        """List all dashboards in a Base app"""
        params = {'page_size': page_size}
        if page_token:
            params['page_token'] = page_token
        return self._make_request('GET', f'/apps/{app_token}/dashboards', params=params)

    def get_dashboard(self, app_token, dashboard_id):
        """Get dashboard information"""
        return self._make_request('GET', f'/apps/{app_token}/dashboards/{dashboard_id}')

    # Convenience methods
    def get_record_by_field_value(self, app_token, table_id, field_name, field_value):
        """Get a record by matching a field value
        
        Args:
            app_token: Base app token
            table_id: Table ID
            field_name: Name of the field to match
            field_value: Value to match against
        
        Returns:
            First record that matches the field value, or None if not found
        """
        filter_exp = f'CurrentValue.[{field_name}] = "{field_value}"'
        result = self.search_records(app_token, table_id, filter_exp=filter_exp, page_size=1)
        records = result.get('data', {}).get('items', [])
        return records[0] if records else None

    def get_or_create_record(self, app_token, table_id, field_name, field_value, additional_fields=None):
        """Get a record by field value or create it if it doesn't exist
        
        Args:
            app_token: Base app token
            table_id: Table ID
            field_name: Name of the field to match
            field_value: Value to match against
            additional_fields: Additional fields to set if creating a new record
        
        Returns:
            Tuple of (record, created) where created is True if a new record was created
        """
        record = self.get_record_by_field_value(app_token, table_id, field_name, field_value)
        if record:
            return record, False
            
        fields = {field_name: field_value}
        if additional_fields:
            fields.update(additional_fields)
        new_record = self.create_record(app_token, table_id, fields)
        return new_record, True

    # Field operations
    def list_fields(self, app_token, table_id, view_id=None, page_size=100, page_token=None):
        """List all fields in a table"""
        params = {'page_size': page_size}
        if view_id:
            params['view_id'] = view_id
        if page_token:
            params['page_token'] = page_token
        return self._make_request('GET', f'/apps/{app_token}/tables/{table_id}/fields', params=params)

    def create_field(self, app_token, table_id, field_name, field_type, property=None):
        """Create a new field in a table"""
        data = {
            'field_name': field_name,
            'type': field_type
        }
        if property:
            data['property'] = property
        return self._make_request('POST', f'/apps/{app_token}/tables/{table_id}/fields', json_data=data)

    def update_field(self, app_token, table_id, field_id, field_name=None, property=None):
        """Update an existing field"""
        data = {}
        if field_name:
            data['field_name'] = field_name
        if property:
            data['property'] = property
        return self._make_request('PUT', f'/apps/{app_token}/tables/{table_id}/fields/{field_id}', json_data=data)

    def delete_field(self, app_token, table_id, field_id):
        """Delete a field from a table"""
        return self._make_request('DELETE', f'/apps/{app_token}/tables/{table_id}/fields/{field_id}')

    # View operations
    def list_views(self, app_token, table_id):
        """List all views in a table"""
        return self._make_request('GET', f'/apps/{app_token}/tables/{table_id}/views')

    def create_view(self, app_token, table_id, view_name, view_type="grid"):
        """Create a new view in a table"""
        data = {
            'view_name': view_name,
            'view_type': view_type
        }
        return self._make_request('POST', f'/apps/{app_token}/tables/{table_id}/views', json_data=data)

    def delete_view(self, app_token, table_id, view_id):
        """Delete a view from a table"""
        return self._make_request('DELETE', f'/apps/{app_token}/tables/{table_id}/views/{view_id}')

    # Role operations
    def list_roles(self, app_token, page_size=100, page_token=None):
        """List all roles in a Base app"""
        params = {'page_size': page_size}
        if page_token:
            params['page_token'] = page_token
        return self._make_request('GET', f'/apps/{app_token}/roles', params=params)

    def create_role(self, app_token, role_name, table_permissions=None):
        """Create a new role"""
        data = {'role_name': role_name}
        if table_permissions:
            data['table_permissions'] = table_permissions
        return self._make_request('POST', f'/apps/{app_token}/roles', json_data=data)

    def update_role(self, app_token, role_id, role_name=None, table_permissions=None):
        """Update an existing role"""
        data = {}
        if role_name:
            data['role_name'] = role_name
        if table_permissions:
            data['table_permissions'] = table_permissions
        return self._make_request('PUT', f'/apps/{app_token}/roles/{role_id}', json_data=data)

    def delete_role(self, app_token, role_id):
        """Delete a role"""
        return self._make_request('DELETE', f'/apps/{app_token}/roles/{role_id}')

    # Form operations
    def get_form(self, app_token, table_id, view_id):
        """Get form information for a view"""
        return self._make_request('GET', f'/apps/{app_token}/tables/{table_id}/forms/{view_id}')

    def create_form_record(self, app_token, table_id, view_id, fields):
        """Create a record through a form view
        
        Args:
            app_token: Base app token
            table_id: Table ID
            view_id: Form view ID
            fields: Dictionary of field values
        """
        data = {'fields': fields}
        return self._make_request('POST', f'/apps/{app_token}/tables/{table_id}/forms/{view_id}/submit', json_data=data)

def group_bot_gen_sign(timestamp, secret):
    # Splicing timestamp and secret
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    # Perform base64 processing on the result
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

def group_bot_send_msg(msg_type, content, webhook_url, webhook_secret):
    """
    ##Bot in group
    https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot

    Webhook:
    https://open.feishu.cn/open-apis/bot/v2/hook/260e63f5-d8bc-4ef7-a058-8cb483d6b42d

    The request body size cannot exceed 20K.
    Image cannot exceed 10 MB
    resolution of other images cannot exceed 12000 x 12000
    """
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

def upload_img_plain(img_path, tenant_access_token):
    # Ref. Server APIMessagingImages messageUpload image
    #      https://open.feishu.cn/document/server-docs/im-v1/image/create
    logging.info('Uploading image...')
    url = "https://open.feishu.cn/open-apis/im/v1/images"
    form = {'image_type': 'message',
            'image': (open(img_path, 'rb'))}  # 需要替换具体的path 
    multi_form = MultipartEncoder(form)
    headers = {
        'Authorization': f'Bearer {tenant_access_token}',
    }
    headers['Content-Type'] = multi_form.content_type
    response = requests.request("POST", url, headers=headers, data=multi_form)
    logging.info(response.headers['X-Tt-Logid'])  # for debug or oncall
    logging.info(response.content)  # Print Response
    assert response.json()['code'] == 0, response.json()
    return response.json()['data']['image_key']

def gen_sign(timestamp, secret):
    # Splicing timestamp and secret
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    # Perform base64 processing on the result
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign


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

def old_main0():
    # Webhook:
    webhook_url = 'https://open.feishu.cn/open-apis/bot/v2/hook/260e63f5-d8bc-4ef7-a058-8cb483d6b42d'
    webhook_secret = 'HgPrBKh4dRTIsa0j4feeRh'

    if 0:
        # Send message
        group_bot_send_msg("text", "Hello, Kiwi!", webhook_url, webhook_secret)


    if 0:
        app_id = 'cli_a7fb15d3f5795013'
        app_secret = 'nqwtqwAiaPJZv3xMYNP7jgBBHiX1pbmB'
        r = get_tenant_access_token(app_id, app_secret)
        print(r)
        tenant_access_token = r['tenant_access_token']
    else:
        tenant_access_token = 't-g104cu4cAQWQ45ABTPL6HSQF5G4555JGMHQ7MMBC'

    # Upload image
    img_path = 'test_bot.webp'
    image_key = upload_img(img_path, tenant_access_token)
    logging.info(image_key)

    if 0:
        # Send message with image
        content = {
            "image_key": image_key
        }
        group_bot_send_msg("image", content, webhook_url, webhook_secret)

    # Ref.
    # https://open.feishu.cn/document/home/develop-a-bot-in-5-minutes/step-5-configure-event-subscription


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
