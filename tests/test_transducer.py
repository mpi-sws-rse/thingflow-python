# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
Tests related to the transducers framework and specific transducers that are
defined in thingflow.filters.transducer
"""

import asyncio
import unittest
from utils import ValueListSensor, ValidationInputThing
from thingflow.base import Scheduler
from thingflow.filters.transducer import SensorSlidingMean, PeriodicMedianTransducer, transduce
from thingflow.filters.combinators import parallel
from thingflow.filters.output import output

value_stream = [
    10,
    11,
    9,
    12,
    15,
    6,
    14,
    9
]

mean_stream = [
    10,
    10.5,
    10,
    10.5,
    11.75,
    10.5,
    11.75,
    11.0
]

periodic_median_stream = [
    10,
    12,
    11.5
]


class TestCase(unittest.TestCase):
    def setUp(self):
        self.scheduler = Scheduler(asyncio.get_event_loop())
        self.sensor = ValueListSensor(1, value_stream)
        
    def test_sensor_event_sliding_window(self):
        vs = ValidationInputThing(mean_stream, self)
        self.scheduler.schedule_sensor(self.sensor, 0.1,
                                       transduce(SensorSlidingMean(4)),
                                       parallel(vs, output()))
        self.scheduler.run_forever()
        self.assertTrue(vs.completed)

    def test_periodic_median_transducer(self):
        vs = ValidationInputThing(periodic_median_stream, self)
        self.scheduler.schedule_sensor(self.sensor, 0.1,
                                       transduce(PeriodicMedianTransducer(3)),
                                       parallel(vs, output()))
        self.scheduler.run_forever()
        self.assertTrue(vs.completed)

if __name__ == '__main__':
    unittest.main()
