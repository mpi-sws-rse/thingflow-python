"""This is a demonstration of the fuctional API for filters. It is
based on examples/rpi/lux_sensor_example.py. See docs/functional-api.rst
for details.
"""
import asyncio
import random
random.seed()

from thingflow.base import InputThing, Scheduler
from thingflow.filters.output import output
from thingflow.filters.select import map
from thingflow.adapters.csv import csv_writer
from thingflow.filters.combinators import passthrough

class DummyLuxSensor:
    def __init__(self, sensor_id, mean=300, stddev=100, stop_after=5):
        """Rather than use the real RPI sensor here, we will just
        define one that generates random numbers.
        """
        self.sensor_id = sensor_id
        self.mean = mean
        self.stddev = stddev
        self.events_left = stop_after

    def sample(self):
        if self.events_left>0:
            data = random.gauss(self.mean, self.stddev)
            self.events_left -= 1
            return data
        else:
            raise StopIteration
        
    def __repr__(self):
        return "DummyLuxSensor(%s, %s, %s)" % \
            (self.sensor_id, self.mean, self.stddev)

class DummyLed(InputThing):
    def on_next(seelf, x):
        if x:
            print("LED ON")
        else:
            print("LED OFF")

    def __repr__(self):
        return 'DummyLed'

THRESHOLD = 300

# Instantiate the sensor and use the functional API to build a flow
lux = DummyLuxSensor("lux-1")
scheduler = Scheduler(asyncio.get_event_loop())
scheduler.schedule_sensor(lux, 1.0,
                          passthrough(output()),
                          passthrough(csv_writer('/tmp/lux.csv')),
                          map(lambda event:event.val > THRESHOLD),
                          passthrough(lambda v: print('ON' if v else 'OFF')),
                          DummyLed(), print_downstream=True)
scheduler.run_forever()
print("That's all folks")
