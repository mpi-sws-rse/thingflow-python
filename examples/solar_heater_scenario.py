"""Implementation ofa solar water heater example (with dummy sensors).

In this scenario, we have a solar water heater that includes a water temperature
sensor on the output pipe of the heater. There is also an actuator which
controls a bypass value: if the actuator is ON, the hot water is redirected to a
Spa, instead of going to the house. The spa is acting as a heat sink, taking
up the extra heat.

The Controller class below implements a state machine which looks at the data
from the temperature sensor and turns on the bypass valve when the heated water
is too hot. To avoid oscillations, we use the following logic:
  1. If the running average of the temperature exceeds T_high, turn on the bypass
  2. When the running average dips below T_low (where T_low<T_high), then turn off the
     bypass.

We also want to aways output an initial value for the valve upon the very first
sensor reading. If the first reading is below T_low, the valve should be off. For
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
INITIAL       | T_high      |         ON   | TOO_HOT
INITIAL       | T_low       |        OFF   | NORMAL
NORMAL        | T_high      |         ON   | TOO_HOT
NORMAL        | between     |       NULL   | NORMAL
NORMAL        | T_low       |       NULL   | NORMAL
TOO_HOT       | T_high      |       NULL   | TOO_HOT
TOO_HOT       | T_low       |        OFF   | NORMAL
TOO_HOT       | between     |       NULL   | TOO_HOT
"""
import asyncio
import time
import random
random.seed()

import antevents.linq.transducer
import antevents.linq.where
import antevents.linq.first
import antevents.linq.dispatch
from antevents.base import Publisher, Scheduler, SensorEvent, SensorPub,\
                           DefaultSubscriber, FatalError

# constants
T_high = 110 # too hot threshold is this in Farenheit
T_low = 100 # reset threshold is this in Farenheit
assert T_low < T_high # to avoid oscillations

# states
INITIAL = "INITIAL"
NORMAL  = "NORMAL"
TOO_HOT ="TOO_HOT"

class DummyTempSensor:
    """Instead of a real temperature sensor, we define one that outputs
    values provided as a list when it is created.
    """
    def __init__(self, sensor_id, values):
        self.sensor_id = sensor_id
        def generator():
            for v in values:
                yield v
        self.generator = generator()

    def sample(self):
        return self.generator.__next__()

    def __repr__(self):
        return 'DummyTempSensor(%s)' % self.sensor_id


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

    def __repr__(self):
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
    
    def on_t_high_next(self, event):
        if self.state==NORMAL or self.state==INITIAL:
            self._dispatch_next(self._make_event("ON"))
            self.state = TOO_HOT

    def on_t_high_completed(self):
        if not self.completed:
            self._dispatch_completed()
            self.completed = True

    def on_t_high_error(self, e):
        pass

    def on_t_low_next(self, event):
        if self.state==TOO_HOT or self.state==INITIAL:
            self._dispatch_next(self._make_event("OFF"))
            self.state = NORMAL

    def on_t_low_completed(self):
        if not self.completed:
            self._dispatch_completed()
            self.completed = True

    def on_t_low_error(self, e):
        pass
            
    def on_between_next(self, x):
        if self.state==INITIAL:
            self.state = NORMAL
            self._dispatch_next(self._make_event("OFF"))
        else:
            pass # stay in current state

    def on_between_error(self, e):
        pass

    def on_between_completed(self):
        pass # don't want to pass this forward, as it will happen after the first item

    def __repr__(self):
        return 'Controller'

class BypassValveActuator(DefaultSubscriber):
    def on_next(self, x):
        if x.val=='ON':
            print("Turning ON!")
        elif x.val=='OFF':
            print("Turning OFF!")
        else:
            raise FatalError("Unexpected event value for actuator: %s" % x.val)

    def __repr__(self):
        return 'BypassValveActuator'


# The values we will use for the sensor
input_sequence = [i for i in range(T_low-2, T_high+4)] + \
                 [i for i in range(T_high+2, T_low-6, -2)] + \
                 [i for i in range(T_low-4, T_high+4, 2)] + \
                 [i for i in range(T_high+2, T_low-6, -2)]
# Add some random noise to our sequence
for i in range(len(input_sequence)):
    input_sequence[i] = round(random.gauss(input_sequence[i], 2), 1)


def run_example():
    sensor = SensorPub(DummyTempSensor('temp-1', input_sequence))
    sensor.output() # let us see the raw values
    dispatcher = sensor.transduce(RunningAvg(4))\
                       .passthrough(lambda evt:
                                    print("Running avg temp: %s" %
                                          round(evt.val, 2))) \
                       .dispatch([(lambda v: v[2]>=T_high, 't_high'),
                                  (lambda v: v[2]<=T_low, 't_low')])
    controller = Controller()
    dispatcher.subscribe(controller, topic_mapping=('t_high', 't_high'))
    dispatcher.subscribe(controller, topic_mapping=('t_low', 't_low'))
    dispatcher.subscribe(controller, topic_mapping=('default', 'between'))
    controller.subscribe(BypassValveActuator())
    sensor.print_downstream()
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_periodic(sensor, 0.5)
    scheduler.run_forever()
    print("got to the end")

        
if __name__ == '__main__':
    run_example()
        
