"""Async adapters to MQTT, using the hbmqtt library.

We can make the send code slightly cleaner by using async/await.
To preverse compatability with Python 3.4, we explicitly queue
up the connect request instead.
"""
import hbmqtt.client
import json
from collections import deque

from antevents.base import DefaultSubscriber, FatalError, Publisher, filtermethod


class QueueWriter(Publisher, DefaultSubscriber):
    def __init__(self, previous_in_chain, uri, topic, scheduler):
        super().__init__()
        self.uri = uri
        self.topic = topic
        self.scheduler = scheduler
        self.connected = False
        self.pending_task = None
        self.pending_message = None
        self.pending_error = None
        self.request_queue = deque()
        self.client = hbmqtt.client.MQTTClient(loop=scheduler.event_loop)
        self.dispose = previous_in_chain.subscribe(self)

    def _to_message(self, x):
        return bytes(json.dumps((x.sensor_id, x.ts, x.val),), encoding='utf-8')
    
    def _process_queue(self, future):
        assert future == self.pending_task
        exc = future.exception()
        if exc:
            raise FatalError("mqtt request failed with exception: " % exc)
        if self.pending_message:
            self._dispatch_next(self.pending_message)
            self.pending_message = None
        if len(self.request_queue)==0:
            self.pending_task = None
            #print("Completed last task")
        else:
            x = self.request_queue.popleft()
            if x is not None:
                self.pending_message = x
                self.pending_task = \
                    self.scheduler._schedule_coroutine(self.client.publish(self.topic,
                                                                           self._to_message(x)),
                                                       self._process_queue)
                #print("enqueuing message %s on %s (from request_q)" %
                #      (repr(x), self.topic))
            else:
                e = self.pending_error
                self.pending_task = \
                    self.scheduler._schedule_coroutine(self.client.disconnect(),
                                                       lambda f: self._dispatch_error(e) if e is not None
                                                       else lambda f: self._dispatch_completed)
                #print("initiated disconnect (pending_error=%s)" % e)
        
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
            self.pending_message = x
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
                                                   lambda f: self._dispatch_error(e))
            #print("on_error: initiated disconnect")
        else:
            self.pending_error = e
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


@filtermethod(Publisher)
def mqtt_async_send(this, uri, topic, scheduler):
    """
    Filter method to send a message on the specified uri and topic. It is
    added to the publisher.
    """
    return QueueWriter(this, uri, topic, scheduler)
