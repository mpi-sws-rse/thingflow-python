"""Async adapters to MQTT, using the hbmqtt library.

We can make the send code slightly cleaner by using async/await.
To preverse compatability with Python 3.4, we explicitly queue
up the connect request instead.
"""
import hbmqtt.client
import hbmqtt.session
import json
import asyncio
from collections import deque

from thingflow.base import InputThing, FatalError, OutputThing, \
                           filtermethod, EventLoopOutputThingMixin


class QueueWriter(OutputThing, InputThing):
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
        self.dispose = previous_in_chain.connect(self)

    def has_pending_requests(self):
        """Return True if there are pending requests. Useful for tests
        without having to expose internal state. Note that, in the event
        of a diconnect(), we don't remove the pending task, as we will be
        calling on_error() or on_completed() directly intead of _process_queue().
        """
        return ((self.pending_task is not None) and  (not self.pending_task.done())) or \
            (self.pending_message is not None) or \
            len(self.request_queue)>0

    def dump_state(self):
        """Return a string representing the internal state
        (for debugging).
        """
        return "QueueWriter(pending_task=%s,pending_message=%s,queue=%s)" %\
            (repr(self.pending_task), repr(self.pending_message),
             repr(self.request_queue))
    
    def _to_message(self, x):
        return bytes(json.dumps((x.sensor_id, x.ts, x.val),), encoding='utf-8')
    
    def _process_queue(self, future):
        assert future == self.pending_task
        exc = future.exception()
        if exc:
            raise FatalError("mqtt request failed with exception: %s" % exc)
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


@filtermethod(OutputThing)
def mqtt_async_send(this, uri, topic, scheduler):
    """
    Filter method to send a message on the specified uri and topic. It is
    added to the output_thing.
    """
    return QueueWriter(this, uri, topic, scheduler)


DELIVER_TIMEOUT=2 # seconds


class QueueReader(OutputThing, EventLoopOutputThingMixin):
    """Subscribe to a topic, wait for incoming messages,
    and push them downstream.
    """
    # state constants
    INITIAL_STATE       = "INITIAL"
    CONNECTING_STATE    = "CONNECTING"
    SUBSCRIBING_STATE   = "SUBSCRIBING"
    ACTIVE_STATE        = "ACTIVE"
    UNSUBSCRIBING_STATE = "UNSUBSCRIBING"
    DISCONNECTING_STATE = "DISCONNECTING"
    FINAL_STATE         = "FINAL"
    
    def __init__(self, uri, topic, scheduler, qos=hbmqtt.client.QOS_1,
                 timeout=DELIVER_TIMEOUT):
        super().__init__()
        self.uri = uri
        self.topic = topic
        self.qos = qos
        self.scheduler = scheduler
        self.state = QueueReader.INITIAL_STATE
        self.pending_task = None
        self.stop_requested = False
        self.client = hbmqtt.client.MQTTClient(loop=scheduler.event_loop)
        self.timeout = timeout # no need to change, overridable just for testing

    def _start_task(self, call, next_state):
        #print("_start_task: %s, next_state=%s" % (repr(call), next_state))
        self.state = next_state
        self.pending_task = self.scheduler._schedule_coroutine(call,
                                                               self._process_event)

    def _process_stop_request(self):
        if self.stop_requested:
            #print("stop requested")
            self._start_task(self.client.unsubscribe([self.topic,]),
                             QueueReader.UNSUBSCRIBING_STATE)
            return True
        else:
            return False
            
    def _process_event(self, future):
        assert future == self.pending_task
        #print("_process_event state=%s" % self.state)
        exc = future.exception()
        if exc and isinstance(exc, asyncio.TimeoutError) and\
           self.state==QueueReader.ACTIVE_STATE:
            # we timeout every few seconds to check for stop requests
            if not self._process_stop_request():
                self._start_task(self.client.deliver_message(self.timeout),
                                 QueueReader.ACTIVE_STATE)
        elif exc:
            raise FatalError("mqtt request failed with exception: %s" % exc)
        elif self.state==QueueReader.CONNECTING_STATE:
            if not self._process_stop_request():
                self._start_task(self.client.subscribe([(self.topic, self.qos),]),
                                                       QueueReader.SUBSCRIBING_STATE)
        elif self.state==QueueReader.SUBSCRIBING_STATE:
            if not self._process_stop_request():
                self._start_task(self.client.deliver_message(self.timeout),
                                 QueueReader.ACTIVE_STATE)
        elif self.state==QueueReader.ACTIVE_STATE:
            result = future.result()
            assert isinstance(result, hbmqtt.session.ApplicationMessage)
            message = str(result.data, encoding='utf-8')
            self._dispatch_next(json.loads(message))
            if not self._process_stop_request():
                self._start_task(self.client.deliver_message(self.timeout),
                                 QueueReader.ACTIVE_STATE)
        elif self.state==QueueReader.UNSUBSCRIBING_STATE:
            self._start_task(self.client.disconnect(),
                             QueueReader.DISCONNECTING_STATE)
        elif self.state==QueueReader.DISCONNECTING_STATE:
            self._dispatch_completed()
            self.state = QueueReader.FINAL_STATE
            self.pending_task = None
            self.scheduler._remove_from_active_schedules(self)
            print("QueueReader in FINAL state")
        elif self.state==QueueReader.FINAL_STATE:
            raise Exception("_process_event should not be called in final state")
        else:
            raise Exception("_process_event: invalidate state %s" % self.state)
            
    def _observe_event_loop(self):
        """This gets things kicked off. Most of the real
        action will occur in _process_event().
        """
        assert self.state == QueueReader.INITIAL_STATE,\
            "_observe_event_loop called when in state %s" % self.state
        self._start_task(self.client.connect(self.uri), QueueReader.CONNECTING_STATE)
        
    def _stop_loop(self):
        """Stop listening for new messages, processing any pending messages, and
        move to the final state.
        """
        self.stop_requested = True
