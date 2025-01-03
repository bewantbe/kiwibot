# test communication to Feishu

from conn_api import *

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
    #old_main()