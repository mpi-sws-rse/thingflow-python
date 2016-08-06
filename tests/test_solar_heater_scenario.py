"""Implementation of the solar water heater example (with dummy sensors).

In this scenario, we have a solar water heater that includes a water temperature
sensor on the output pipe of the heater. There is also an actuator which
controls a bypass value: if the actuator is ON, the water goes directly to the
Spa, without going through the Solar heater.

The Controller class below implements a state machine which looks at the data
from the temperature sensor and turns on the bypass valve when the heated water
is too hot. To avoid oscillations, we use the following logic:
  1. If the running average of the temperature exceeds T1, turn on the bypass
  2. When the running average dips below T2 (where T2<T1), then turn off the
     bypass.

We also want to aways output an initial value for the valve upon the very first
sensor reading. If the first reading is below T2, the valve should be off. For
subsequent sensor events, we only output an actuator value if it has changed.

When designing the graph for this application, we need to ensure that we
have input determinism: for a given input sequence, only one output sequence
on the actuator is possible. This can be achieved by using the dispatch()
filter, which ensures that only one event is input to the controller state
machine for a given sensor input.

Here is the spec for out state machine:

Current State | Input Event | Output Event | Next State
==============+=============+==============+=============
INITIAL       | between     |        OFF   | NORMAL
INITIAL       | T1          |         ON   | TOO_HOT
INITIAL       | T2          |        OFF   | NORMAL
NORMAL        | T1          |         ON   | TOO_HOT
NORMAL        | T2          |       NULL   | NORMAL
TOO_HOT       | T1          |       NULL   | TOO_HOT
TOO_HOT       | T2          |        OFF   | NORMAL
"""
import asyncio
import unittest

import antevents.linq.transducer
import antevents.linq.where
import antevents.linq.first
import antevents.linq.dispatch
from antevents.base import *
from utils import ValidationSubscriber

# constants
T1 = 120 # too hot threshold is this in Farenheit
T2 = 100 # reset threshold is this in Farenheit
assert T2 < T1 # to avoid oscillations

# states
INITIAL = "INITIAL"
NORMAL  = "NORMAL"
TOO_HOT ="TOO_HOT"

class RunningAvg(antevents.linq.transducer.Transducer):
    """Transducer that returns a running average of values
    of over the history interval. Note that the interval is a time period,
    not a number of samples.
    """
    def __init__(self, history_interval):
        self.history_interval = history_interval
        self.history = [] # first element in the list is the oldest

    def step(self, event):
        total = event.val # always include the latest
        cnt = 1
        new_start = 0
        for (i, old_event) in enumerate(self.history):
            if (event.ts-old_event.ts)<self.history_interval:
                total += old_event.val
                cnt += 1
            else: # the timestamp is stale
                new_start = i + 1 # will at least start at the next one
        if new_start>0:
            self.history = self.history[new_start:]
        self.history.append(event)
        return SensorEvent(ts=event.ts, sensor_id=event.sensor_id, val=total/cnt)

    def __str__(self):
        return 'RunningAvg(%s)' % self.history_interval


class Controller(Publisher):
    """Input sensor events and output actuator settings.
    """
    def __init__(self):
        super().__init__()
        self.state = INITIAL
        self.completed = False

    def _make_event(self, val):
        return SensorEvent(ts=time.time(), sensor_id='Controller', val=val)
    
    def on_t1_next(self, event):
        if self.state==NORMAL or self.state==INITIAL:
            self._dispatch_next(self._make_event("ON"))
            self.state = TOO_HOT

    def on_t1_completed(self):
        if not self.completed:
            self._dispatch_completed()
            self.completed = True

    def on_t1_error(self, e):
        pass

    def on_t2_next(self, event):
        if self.state==TOO_HOT or self.state==INITIAL:
            self._dispatch_next(self._make_event("OFF"))
            self.state = NORMAL

    def on_t2_completed(self):
        if not self.completed:
            self._dispatch_completed()
            self.completed = True

    def on_t2_error(self, e):
        pass
            
    def on_between_next(self, x):
        assert self.state==INITIAL, "Should only get between on the first call"
        self.state = NORMAL
        self._dispatch_next(self._make_event("OFF"))

    def on_between_error(self, e):
        pass

    def on_between_completed(self):
        pass # don't want to pass this forward, as it will happen after the first item

    
def sensor_from_sequence(sensor_id, sequence):
    """Return a sensor that samples from a sequence of (ts, value) pairs.
    """
    def generator():
        for (ts, v) in sequence:
            yield SensorEvent(sensor_id, ts, v)

    o = IterableAsPublisher(generator(), name='Sensor(%s)' % sensor_id)
    return o


input_sequence = [(1, T1-5), (2, T1), (3, T1+2), (4, T1+2),
                  (5, T2), (6, T2), (7, T2-1), (8, T2-2)]

expected_sequence= ['OFF', 'ON', 'OFF']

class TestSolarHeater(unittest.TestCase):
    def test_case(self):
        sensor = sensor_from_sequence(1, input_sequence)
        sensor.subscribe(print)
        dispatcher = sensor.transduce(RunningAvg(2)) \
                           .dispatch([(lambda v: v[2]>=T1, 't1'),
                                      (lambda v: v[2]<=T2, 't2')])
        controller = Controller()
        dispatcher.subscribe(controller, topic_mapping=('t1', 't1'))
        dispatcher.subscribe(controller, topic_mapping=('t2', 't2'))
        # we only push the between message to the controller for the first
        # event - it is only needed for emitting an output from the initial
        # state.
        dispatcher.first().subscribe(controller, topic_mapping=('default',
                                                                'between'))
        controller.subscribe(print)
        vo = ValidationSubscriber(expected_sequence, self)
        controller.subscribe(vo)
        sensor.print_downstream()
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(sensor, 0.5)
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")
        print("got to the end")

if __name__ == '__main__':
    unittest.main()
        
