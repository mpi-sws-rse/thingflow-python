"""This version uses a traditional event-driven version,
using continuation passing style. Each method call is passed
a completion callback and an error callback
"""
from statistics import median
import json
import asyncio
import random
import time
import hbmqtt.client
from collections import deque

from thingflow.base import SensorEvent

URL = "mqtt://localhost:1883"

class RandomSensor:
    def __init__(self, sensor_id, mean=100.0, stddev=20.0, stop_after_events=None):
        self.sensor_id = sensor_id
        self.mean = mean
        self.stddev = stddev
        self.stop_after_events = stop_after_events
        if stop_after_events is not None:
            def generator():
                for i in range(stop_after_events):
                    yield round(random.gauss(mean, stddev), 1)
        else: # go on forever
            def generator():
                while True:
                    yield round(random.gauss(mean, stddev), 1)
        self.generator = generator()

    def sample(self):
        return self.generator.__next__()

    def __repr__(self):
        if self.stop_after_events is None:
            return 'RandomSensor(%s, mean=%s, stddev=%s)' % \
                (self.sensor_id, self.mean, self.stddev)
        else:
            return 'RandomSensor(%s, mean=%s, stddev=%s, stop_after_events=%s)' % \
                (self.sensor_id, self.mean, self.stddev, self.stop_after_events)

class PeriodicMedianTransducer:
    """Emit an event once every ``period`` input events.
    The value is the median of the inputs received since the last
    emission.
    """
    def __init__(self, period=5):
        self.period = period
        self.samples = [None for i in range(period)]
        self.events_since_last = 0
        self.last_event = None # this is used in emitting the last event
    
    def step(self, v):
        self.samples[self.events_since_last] = v.val
        self.events_since_last += 1
        if self.events_since_last==self.period:
            val = median(self.samples)
            event = SensorEvent(sensor_id=v.sensor_id, ts=v.ts, val=val)
            self.events_since_last = 0
            return event
        else:
            self.last_event = v # save in case we complete before completing a period
            return None

    def complete(self):
        if self.events_since_last>0:
            # if we have some partial state, we emit one final event that
            # averages whatever we saw since the last emission.
            return SensorEvent(sensor_id=self.last_event.sensor_id,
                               ts=self.last_event.ts,
                               val=median(self.samples[0:self.events_since_last]))


def csv_writer(evt):
    print("csv_writer(%s)" % repr(evt))

class MqttWriter:
    """All the processing is asynchronous. We ensure that a given send has
    completed and the callbacks called before we process the next one.
    """
    def __init__(self, url, topic, event_loop):
        self.url = url
        self.topic = topic
        self.client = hbmqtt.client.MQTTClient(loop=event_loop)
        self.event_loop = event_loop
        self.connected = False
        self.pending_task = None
        self.request_queue = deque()

    def _to_message(self, msg):
        return bytes(json.dumps((msg.sensor_id, msg.ts, msg.val),), encoding='utf-8')

    def _request_done(self, f, completion_cb, error_cb):
        assert f==self.pending_task
        self.pending_task = None
        exc = f.exception()
        if exc:
            self.event_loop.call_soon(error_cb, exc)
        else:
            self.event_loop.call_soon(completion_cb)
        if len(self.request_queue)>0:
            self.event_loop.call_soon(self._process_queue)
    
    def _process_queue(self):
        assert self.pending_task == None
        assert len(self.request_queue)>0
        (msg, completion_cb, error_cb) = self.request_queue.popleft()
        if msg is not None:
            print("send from queue: %s" % msg)
            self.pending_task = self.event_loop.create_task(
                self.client.publish(self.topic, msg)
            )
        else: # None means that we wanted a disconnect
            print("disconnect")
            self.pending_task = self.event_loop.create_task(
                self.client.disconnect()
            )
        self.pending_task.add_done_callback(lambda f:
                                            self._request_done(f, completion_cb,
                                                               error_cb))        
    def send(self, msg, completion_cb, error_cb):
        if not self.connected:
            print("attempting connection")
            self.request_queue.append((self._to_message(msg),
                                       completion_cb, error_cb),)
            self.connected = True
            self.pending_task = self.event_loop.create_task(self.client.connect(self.url))
            def connect_done(f):
                assert f==self.pending_task
                print("connected")
                self.pending_task = None
                self.event_loop.call_soon(self._process_queue)
            self.pending_task.add_done_callback(connect_done)
        elif self.pending_task:
            self.request_queue.append((self._to_message(msg), completion_cb,
                                       error_cb),)
        else:
            print("sending %s" % self._to_message(msg))
            self.pending_task = self.event_loop.create_task(
                self.client.publish(self.topic, self._to_message(msg))
            )
            self.pending_task.add_done_callback(lambda f:
                                                self._request_done(f, completion_cb,
                                                                   error_cb))                    

    def disconnect(self, completion_cb, error_cb, drop_queue=False):
        if not self.connected:
            return
        if len(self.request_queue)>0 and drop_queue: # for error situations
            self.request_queue = deque()
        if self.pending_task:
            self.request_queue.append((None, completion_cb, error_cb),)
        else:
            print("disconnecting")
            self.pending_task = self.event_loop.create_task(
                self.client.disconnect()
            )
            self.pending_task.add_done_callback(lambda f:
                                                self._request_done(f, completion_cb,
                                                                   error_cb))

def sample_and_process(sensor, mqtt_writer, xducer, completion_cb, error_cb):
    try:
        sample = sensor.sample()
    except StopIteration:
        final_event = xducer.complete()
        if final_event:
            mqtt_writer.send(final_event,
                             lambda: mqtt_writer.disconnect(lambda: completion_cb(False), error_cb),
                             error_cb)
        else:
            mqtt_writer.disconnect(lambda: completion_cb(False), error_cb)
        return
    event = SensorEvent(sensor_id=sensor.sensor_id, ts=time.time(), val=sample)
    csv_writer(event)
    median_event = xducer.step(event)
    if median_event:
        mqtt_writer.send(median_event,
                         lambda: completion_cb(True), error_cb)
    else:
        completion_cb(True)

        
sensor = RandomSensor('sensor-2', stop_after_events=12)
transducer = PeriodicMedianTransducer(5)
event_loop = asyncio.get_event_loop()
writer = MqttWriter(URL, sensor.sensor_id, event_loop)

def loop():
    def completion_cb(more):
        if more:
            event_loop.call_later(0.5, loop)
        else:
            print("all done, no more callbacks to schedule")
            event_loop.stop()
    def error_cb(e):
        print("Got error: %s" % e)
        event_loop.stop()
    event_loop.call_soon(
        lambda: sample_and_process(sensor, writer, transducer,
                                   completion_cb, error_cb)
    )


event_loop.call_soon(loop)
event_loop.run_forever()
    

print("that's all folks")
