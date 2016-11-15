"""This version uses the async and await calls.
"""
from statistics import median
import json
import asyncio
import random
import time
import hbmqtt.client

from antevents.base import SensorEvent

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
    def __init__(self, url, topic, event_loop):
        self.url = url
        self.topic = topic
        self.client = hbmqtt.client.MQTTClient(loop=event_loop)
        self.connected = False

    def _to_message(self, msg):
        return bytes(json.dumps(msg), encoding='utf-8')
    
    async def send(self, msg):
        if not self.connected:
            print("attempting connection")
            await self.client.connect(self.url)
            self.connected = True
            print("connected")
        print("sending %s" % self._to_message(msg))
        await self.client.publish(self.topic, self._to_message(msg))

    async def disconnect(self):
        if self.connected:
            await self.client.disconnect()


async def sample_and_process(sensor, mqtt_writer, xducer):
    try:
        sample = sensor.sample()
    except StopIteration:
        final_event = xducer.complete()
        if final_event:
            await mqtt_writer.send((final_event.sensor_id, final_event.ts,
                                    final_event.val),)
        print("disconnecting")
        await mqtt_writer.disconnect()
        return False
    event = SensorEvent(sensor_id=sensor.sensor_id, ts=time.time(), val=sample)
    csv_writer(event)
    median_event = xducer.step(event)
    if median_event:
        await mqtt_writer.send((median_event.sensor_id, median_event.ts,
                                median_event.val),)
    return True
        
        
    
sensor = RandomSensor('sensor-2', stop_after_events=12)
transducer = PeriodicMedianTransducer(5)
event_loop = asyncio.get_event_loop()
writer = MqttWriter(URL, sensor.sensor_id, event_loop)

def loop():
    coro = sample_and_process(sensor, writer, transducer)
    task = event_loop.create_task(coro)
    def done_callback(f):
        exc = f.exception()
        if exc:
            raise exc
        elif f.result()==False:
            print("all done, no more callbacks to schedule")
            event_loop.stop()
        else:
            event_loop.call_later(0.5, loop)
    task.add_done_callback(done_callback)


event_loop.call_soon(loop)
event_loop.run_forever()
    

print("that's all folks")
