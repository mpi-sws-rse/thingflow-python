"""
Comparing AntEvents to generic asyncio programming.

This is the AntEvents version.
"""
import asyncio
import random
from statistics import median
from antevents.base import DefaultSubscriber, SensorEvent, Scheduler, SensorPub
from antevents.linq.transducer import Transducer
import antevents.linq.combinators
import antevents.adapters.csv
from antevents.adapters.mqtt_async import QueueWriter

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

class PeriodicMedianTransducer(Transducer):
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

SENSOR_ID = 'sensor-1'
scheduler = Scheduler(asyncio.get_event_loop())
sensor = SensorPub(RandomSensor(SENSOR_ID, mean=10, stddev=5, stop_after_events=12))
sensor.passthrough(lambda e: print('raw event: %s' % repr(e))).csv_writer('raw_data.csv')
writer = QueueWriter(URL, SENSOR_ID, scheduler)
sensor.transduce(PeriodicMedianTransducer()).subscribe(writer)
scheduler.schedule_periodic(sensor, 0.5)
scheduler.run_forever()
print("that's all folks")
