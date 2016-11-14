"""Async adapters to MQTT, using the hbmqtt library.

We can make the send code slightly cleaner by using async/await.
To preverse compatability with Python 3.4, we explicitly queue
up the connect request instead.
"""
import hbmqtt.client
import json
from collections import deque

from antevents.base import DefaultSubscriber, FatalError


class QueueWriter(DefaultSubscriber):
    def __init__(self, uri, topic, scheduler):
        self.uri = uri
        self.topic = topic
        self.scheduler = scheduler
        self.connected = False
        self.pending_task = None
        self.request_queue = deque()
        self.client = hbmqtt.client.MQTTClient(loop=scheduler.event_loop)

    def _to_message(self, x):
        return bytes(json.dumps((x.sensor_id, x.ts, x.val),), encoding='utf-8')
    
    def _process_queue(self, future):
        assert future == self.pending_task
        exc = future.exception()
        if exc:
            raise FatalError("mqtt request failed with exception: " % exc)
        if len(self.request_queue)==0:
            self.pending_task = None
            #print("Completed last task")
        else:
            x = self.request_queue.popleft()
            if x is not None:
                self.pending_task = \
                    self.scheduler._schedule_coroutine(self.client.publish(self.topic,
                                                                           self._to_message(x)),
                                                       self._process_queue)
                #print("enqueuing message %s on %s (from request_q)" %
                #      (repr(x), self.topic))
            else:
                self.pending_task = \
                    self.scheduler._schedule_coroutine(self.client.disconnect(),
                                                       self._process_queue)
                #print("initiated disconnect")
        
    def on_next(self, x):
        if self.connected == False:
            self.request_queue.append(x)
            self.pending_task = \
                self.scheduler._schedule_coroutine(self.client.connect(self.uri),
                                                   self._process_queue)
            self.connected = True
            #print("connection in progress, put message %s on request_queue"
            #      % repr(x))
        elif self.pending_task is not None:
            self.request_queue.append(x)
            #print("put message %s on request_queue" % repr(x))
        else:
            self.pending_task = \
                self.scheduler._schedule_coroutine(self.client.publish(self.topic, self._to_message(x)),
                                                   self._process_queue)
            #print("enqueuing message %s on %s" % (repr(x), self.topic))

    def on_error(self, e):
        if len(self.request_queue)>0:
            # empty the pending request queue, we won't try to
            # send these.
            self.request_queue = deque()
            #print("on_error: dropped pending requests")
        if self.pending_task is None:
            self.pending_task = \
                self.scheduler._schedule_coroutine(self.client.disconnect(),
                                                   self._process_queue)
            #print("on_error: initiated disconnect")
        else:
            self.request_queue.append(None)
            #print("on_error: queued disconnect")
            
    
    def on_completed(self):
        if self.pending_task is None:
            self.pending_task = \
                self.scheduler._schedule_coroutine(self.client.disconnect(),
                                                   self._process_queue)
            #print("on_completed: initiated disconnect")
        else:
            self.request_queue.append(None)
            #print("on_completed: queued disconnect")
