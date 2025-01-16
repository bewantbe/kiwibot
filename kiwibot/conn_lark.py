# interface for communication
# so far mostly Feishu

import os
import time
import logging
import json

import threading
import queue

import requests
from dotenv import load_dotenv
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateImageRequest, CreateImageRequestBody, CreateImageResponse,
    CreateMessageRequest, CreateMessageRequestBody, CreateMessageResponse,
    ReplyMessageRequest, ReplyMessageRequestBody, ReplyMessageResponse,
    P2ImMessageReceiveV1,
    GetChatResponse, GetChatRequest,
)

from lark_oapi.api.contact.v3 import (
    BatchUserResponse, BatchUserRequest,
    GetUserRequest, GetUserResponse,
)

from utils import (
    GetISOTimestamp,
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

class FeishuChatTool:
    """Basic functions for chating in Feishu"""
    def __init__(self, client, feishu_log_level):
        self.client = client
        self.message_recv_cb = None
        self.lark_log_level = feishu_log_level
    
    def send_message_plain(self, msg):
        content = json.dumps(msg['content'])
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(msg['chat_id'])
                .msg_type(msg['message_type'])
                .content(content)
                .build()
            )
            .build()
        )
        response = self.client.im.v1.chat.create(request)
        return response, "client.im.v1.chat.create failed"
    
    def send_message_reply(self, msg):
        content = json.dumps(msg['content'])
        request: ReplyMessageRequest = (
            ReplyMessageRequest.builder()
            .message_id(msg['message_id'])
            .request_body(
                ReplyMessageRequestBody.builder()
                .content(content)
                .msg_type(msg['message_type'])
                .build()
            )
            .build()
        )
        response: ReplyMessageResponse = self.client.im.v1.message.reply(request)
        return response, "client.im.v1.message.reply"
    
    def send_message(self, msg):
        """Send message to user or group
        Deal with message depends on the type"""
        if msg['message_id'] is None:
            response, call_name = self.send_message_plain(msg)
        else:
            # replay to message
            response, call_name = self.send_message_reply(msg)

        if not response.success():
            raise Exception(
                f"{call_name} failed, code: {response.code}, "
                f"msg: {response.msg}, log_id: {response.get_log_id()}"
            )

    def register_message_callback_and_start(self, cb_func):
        self.message_recv_cb = cb_func
        event_handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self.message_recv_cb)
            # more action_trigger can be attached here
            # Ref. https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/event-subscription-guide/callback-subscription/configure-callback-request-address
            .build()
        )
        # websocket service for callback
        self.ws_client = lark.ws.Client(
            self.client._config.app_id,
            self.client._config.app_secret,
            event_handler = event_handler,
            log_level = self.lark_log_level,
        )
        def start_ws_client():
            self.ws_client.start()  # this is blocking

        thread = threading.Thread(target=start_ws_client)
        thread.daemon = True
        thread.start()              # this is non-blocking
        self.ws_thread = thread

    def cb_message_to_chat_message(self, payload):
        """Convert P2ImMessageReceiveV1 to message-like dict"""
        message = payload.event.message
        msg = {
            "chat_id": message.chat_id,
            "chat_type": message.chat_type,
            "sender_id": payload.event.sender.sender_id.open_id,
            "message_id": message.message_id,
            "message_type": message.message_type,
            "content": json.loads(message.content),
            "mentions": None,
            "timestamp": GetISOTimestamp(int(message.create_time)/1000),
            "update_time": GetISOTimestamp(int(message.update_time)/1000),
        }
        if message.mentions is not None:
            msg["mentions"] = [
                {
                    'key': it.key,
                    'name': it.name,
                    'tenant_key': it.tenant_key,
                    'id': {
                        'open_id': it.id.open_id,
                        'union_id': it.id.union_id,
                        'user_id': it.id.user_id,
                    }
                } for it in message.mentions]
        return msg

    def get_group_info(self, chat_id):
        """Get group info"""
        request: GetChatRequest = GetChatRequest.builder() \
            .chat_id(chat_id) \
            .build()
        response: GetChatResponse = self.client.im.v1.chat.get(request)
        return response

    def get_user_info_batch(self, user_id_list):
        """Get user info"""
        request: BatchUserRequest = BatchUserRequest.builder() \
            .user_ids(user_id_list) \
            .user_id_type("open_id") \
            .department_id_type("open_department_id") \
            .build()

        # 发起请求
        response: BatchUserResponse = self.client.contact.v3.user.batch(request)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.contact.v3.user.batch failed, code: {response.code},"
                f"msg: {response.msg},"
                f"log_id: {response.get_log_id()},"
                f"resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # 处理业务结果
        lark.logger.info(lark.JSON.marshal(response.data, indent=4))
        return response

    def get_user_info(self, user_id):
        """Get single user info"""
        request: GetUserRequest = GetUserRequest.builder() \
            .user_id(user_id) \
            .user_id_type("open_id") \
            .department_id_type("open_department_id") \
            .build()

        # 发起请求
        response = self.client.contact.v3.user.get(request)
        # json.loads(response.raw.content)
        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.contact.v3.user.get failed, code: {response.code},"
                f"msg: {response.msg},"
                f"log_id: {response.get_log_id()},"
                f"resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # 处理业务结果
        lark.logger.info(lark.JSON.marshal(response.data, indent=4))
        return response

    def get_group_name(self, chat_id):
        # TODO: cache group name in file
        response = self.get_group_info(chat_id)
        return response.data.name

    def get_user_name(self, user_id):
        # cache user name in file
        response = self.get_user_info(user_id)
        return response.data.user.name

def is_at_user(msg, user_name):
    return msg['mentions'] is not None \
        and len(msg['mentions']) > 0 \
        and msg['mentions'][0]['name'] == user_name

def simple_msg_by(ref_msg, sender, text, is_reply = None):
    if is_reply is None:
        is_reply = is_at_user(ref_msg, sender)
    ts = GetISOTimestamp()
    response = {
        'chat_id': ref_msg['chat_id'],        # reply to this p2p chat
        'chat_type': ref_msg['chat_type'],
        'sender_id': sender,                  # only for log
        'message_id': ref_msg['message_id'] if is_reply else None,  # reply to this message in group chat
        'message_type': 'text',
        'content': {
            'text': text
        },
        'timestamp': ts,
        'update_time': ts
    }
    return response

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
        self.lock_db = threading.Lock()
        self.app_id = app_id
        self.app_secret = app_secret

        self.chattool = FeishuChatTool(self.client, self.lark_log_level)
        self.chattool.register_message_callback_and_start(self._on_message_received)
        self._start_sending_thread()

    def _on_message_received(self, data: P2ImMessageReceiveV1):
        msg = self.chattool.cb_message_to_chat_message(data)
        self._log_communication(msg)
        if msg["content"].get("text") == "whoami":
            # special rule
            name = self.chattool.get_user_name(msg["sender_id"])
            msg = simple_msg_by(msg, 'bot', f"You are {name}")
            self.send_message(msg)
        else:
            # general chat
            self.recv_queue.put(msg)

    def send_message(self, msg):
        self.chattool.send_message(msg)
        self._log_communication(msg)

    def _log_communication(self, message_log):
        with self.lock_db:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(message_log, indent=4) + '\n')

    def _start_sending_thread(self):
        def send_from_queue():
            while True:
                msg = self.send_queue.get()
                if msg is not None:
                    self.send_message(msg)
                self.send_queue.task_done()

        thread = threading.Thread(target=send_from_queue)
        thread.daemon = True
        thread.start()
        self.sending_thread = thread

if __name__ == '__main__':
    load_dotenv()
    print('Start main')

    # echo bot
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
