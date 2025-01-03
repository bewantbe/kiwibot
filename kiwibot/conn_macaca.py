# 

import threading
import queue
import time

class MessageRouter(threading.Thread):
    def __init__(self):
        super().__init__()
        self.recv_queue = None
        self.send_queue = None
        self.timed_events = []
        self.running = True

    def register_queues(self, recv_queue, send_queue):
        self.recv_queue = recv_queue
        self.send_queue = send_queue

    def register_timed_event(self, interval, message):
        event = threading.Event()
        self.timed_events.append((interval, message, event))
        threading.Thread(target=self._timed_event_handler,
                         args=(interval, message, event)).start()

    def _timed_event_handler(self, interval, message, event):
        while not event.is_set():
            time.sleep(interval)
            if self.send_queue:
                self.send_queue.put(message)

    def run(self):
        while self.running:
            if self.recv_queue:
                try:
                    msg = self.recv_queue.get(timeout=1)
                    if self.send_queue:
                        msg['content']['text'] = f"Received: {msg['content']['text']}"
                        self.send_queue.put(f"Received: {msg}")
                except queue.Empty:
                    continue

    def stop(self):
        self.running = False
        for _, _, event in self.timed_events:
            event.set()