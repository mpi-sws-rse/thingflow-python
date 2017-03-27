"""A simple example to demonstrate a thing with multiple ports. The 
thing samples values from a sensor and sends them on different output
ports depending on the divisibility of the value. See docs/ports.rst
for a more detailed explanation.
"""
import random
import asyncio
from thingflow.base import OutputThing, InputThing, Scheduler,\
                           SensorAsOutputThing

class MultiPortOutputThing(OutputThing, InputThing):
    def __init__(self, previous_in_chain):
        super().__init__(ports=['divisible_by_two', 'divisible_by_three',
                                 'other'])
        # connect to the previous filter
        self.disconnect_from_upstream = previous_in_chain.connect(self)
        
    def on_next(self, x):
        val = int(round(x.val))
        if (val%2)==0:
            self._dispatch_next(val, port='divisible_by_two')
        if (val%3)==0:
            self._dispatch_next(val, port='divisible_by_three')
        if (val%3)!=0 and (val%2)!=0:
            self._dispatch_next(val, port='other')

    def on_completed(self):
        self._dispatch_completed(port='divisible_by_two')
        self._dispatch_completed(port='divisible_by_three')
        self._dispatch_completed(port='other')
        
    def on_error(self, e):
        self._dispatch_error(e, port='divisible_by_two')
        self._dispatch_error(e, port='divisible_by_three')
        self._dispatch_error(e, port='other')
    
    def __repr__(self):
        return 'MultiPortOutputThing()'

class RandomSensor:
    def __init__(self, sensor_id, mean=100.0, stddev=20.0, stop_after_events=None):
        self.sensor_id = sensor_id
        self.mean = mean
        self.stddev = stddev
        self.stop_after_events = stop_after_events
        if stop_after_events is not None:
            def generator():
                for i in range(stop_after_events):
                    yield random.gauss(mean, stddev)
        else: # go on forever
            def generator():
                while True:
                    yield random.gauss(mean, stddev)
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


scheduler = Scheduler(asyncio.get_event_loop())
sensor = SensorAsOutputThing(RandomSensor(1, mean=10, stddev=5,
                                          stop_after_events=10))
mtthing = MultiPortOutputThing(sensor)
mtthing.connect(lambda v: print("even: %s" % v),
                port_mapping=('divisible_by_two', 'default'))
mtthing.connect(lambda v: print("divisible by three: %s" % v),
                port_mapping=('divisible_by_three', 'default'))
mtthing.connect(lambda v: print("not divisible: %s" % v),
                port_mapping=('other', 'default'))
mtthing.print_downstream()
scheduler.schedule_recurring(sensor)
scheduler.run_forever()

