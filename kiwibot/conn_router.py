# 

import threading
import queue
import time
import copy

class MessageRouter(threading.Thread):
    def __init__(self, recv_queue, send_queue):
        super().__init__()
        self.recv_queue = recv_queue
        self.send_queue = send_queue
        self.timed_events = {}
        self.running = True
        self.timer_id_counter = 0
        self.message_dealer = lambda x: f"Received: {x}"

    def register_timed_event(self, interval, user_name, action_string):
        message = {
            "chat_type": "p2p",
            "message_type": "text",
            "chat_id": "oc_11b180e1d953d36f1b2a85c849be703f",   # User name
            #"message_id": "om_f414a08b7383067ff3927a91e7e480c8",
            "sender_id": "ou_0b2ada4556de2f7b7ddc6557b6f4292b",
            "update_time": "2025-01-04T01:55:43.947",
            "content": {
                "text": action_string
            }
        }
        event = threading.Event()
        timer_id = self.timer_id_counter
        self.timer_id_counter += 1
        self.timed_events[timer_id] = (interval, message, event)
        threading.Thread(target=self._timed_event_handler,
                         args=(interval, message, event)).start()
        return timer_id

    def unregister_timed_event(self, timer_id):
        if timer_id in self.timed_events:
            _, _, event = self.timed_events[timer_id]
            event.set()
            del self.timed_events[timer_id]

    def _timed_event_handler(self, interval, message, event):
        while not event.is_set():
            interrupted = event.wait(interval)
            if not interrupted and self.send_queue:
                response = self._action_then_response(message)
                self.send_queue.put(response)

    def set_message_dealer(self, message_dealer):
        self.message_dealer = message_dealer

    def _single_response(self, msg):
        response = copy.deepcopy(msg)
        response['content']['text'] = self.message_dealer(msg['content']['text'])
        return response

    def _action_then_response(self, msg):
        response = copy.deepcopy(msg)
        todo = msg['content']['text']
        if todo == 'time':
            response['content']['text'] = f"Time now: {time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}"
        return response

    def run(self):
        while self.running:
            if self.recv_queue:
                try:
                    msg = self.recv_queue.get(timeout=1)
                    if self.send_queue:
                        response = self._single_response(msg)
                        self.send_queue.put(response)
                except queue.Empty:
                    continue

    def stop(self):
        self.running = False
        for timer_id in list(self.timed_events.keys()):
            self.unregister_timed_event(timer_id)
