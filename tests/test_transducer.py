"""
Tests related to the transducers framework and specific transducers that are
defined in antevents.linq.transducer
"""

import asyncio
import unittest
from utils import make_test_sensor_from_vallist, ValidationSubscriber
from antevents.base import Scheduler
from antevents.linq.transducer import SensorSlidingMean

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
        self.sensor = make_test_sensor_from_vallist(1, value_stream)
        
    def test_sensor_event_sliding_window(self):
        o = self.sensor.transduce(SensorSlidingMean(4)).output()
        vs = ValidationSubscriber(mean_stream, self)
        o.subscribe(vs)
        self.sensor.print_downstream()
        self.scheduler.schedule_recurring(self.sensor)
        self.scheduler.run_forever()
        self.assertTrue(vs.completed)


if __name__ == '__main__':
    unittest.main()
