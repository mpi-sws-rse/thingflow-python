"""
Tests related to the transducers framework and specific transducers that are
defined in antevents.linq.transducer
"""

import asyncio
import unittest
from utils import ValueListSensor, ValidationSubscriber
from antevents.base import Scheduler
from antevents.linq.transducer import SensorSlidingMean, transduce_fn
from antevents.linq.combinators import parallel
from antevents.linq.output import output

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

class TestCase(unittest.TestCase):
    def setUp(self):
        self.scheduler = Scheduler(asyncio.get_event_loop())
        self.sensor = ValueListSensor(1, value_stream)
        
    def test_sensor_event_sliding_window(self):
        vs = ValidationSubscriber(mean_stream, self)
        self.scheduler.schedule_sensor(self.sensor, 0.1,
                                       transduce_fn(SensorSlidingMean(4)),
                                       parallel(vs, output))
        self.scheduler.run_forever()
        self.assertTrue(vs.completed)


if __name__ == '__main__':
    unittest.main()
