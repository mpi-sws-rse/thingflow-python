"""These tests are designed to be run on a desktop. You can use
them to validate the system before deploying to 8266. They use stub
sensors.

Test the core antevents functionality - the base.py module.
"""

import sys
import os
import os.path
import time

try:
    import antevents_upython
except ImportError:
    sys.path.append(os.path.abspath('../'))
    import antevents_upython

import unittest

from antevents_upython.base import *
from antevents_upython.utils import get_logger, initialize_logging, close_logging

class DummySensor(object):
    def __init__(self, value_stream, sample_time=0):
        self.value_stream = value_stream
        self.idx = 0
        self.sample_time = sample_time

    def sample(self):
        if self.idx==len(self.value_stream):
            raise StopSensor()
        else:
            if self.sample_time > 0:
                print("Sensor simulating a sample time of %d seconds with a sleep" %
                      self.sample_time)
                time.sleep(self.sample_time)
            val = self.value_stream[self.idx]
            self.idx += 1
            return val

    def __str__(self):
        return 'DummySensor'

class ValidationSubscriber(DefaultSubscriber):
    """Compare the values in a event stream to the expected values.
    Use the test_case for the assertions (for proper error reporting in a unit
    test).
    """
    def __init__(self, expected_stream, test_case,
                 extract_value_fn=lambda event:event.val):
        self.expected_stream = expected_stream
        self.next_idx = 0
        self.test_case = test_case
        self.extract_value_fn = extract_value_fn
        self.completed = False

    def on_next(self, x):
        tc = self.test_case
        tc.assertLess(self.next_idx, len(self.expected_stream),
                      "Got an event after reaching the end of the expected stream")
        expected = self.expected_stream[self.next_idx]
        actual = self.extract_value_fn(x)
        tc.assertEqual(actual, expected,
                       "Values for element %d of event stream mismatch" % self.next_idx)
        self.next_idx += 1

    def on_completed(self):
        tc = self.test_case
        tc.assertEqual(self.next_idx, len(self.expected_stream),
                       "Got on_completed() before end of stream")
        self.completed = True

    def on_error(self, exc):
        tc = self.test_case
        tc.assertTrue(False,
                      "Got an unexpected on_error call with parameter: %s" % exc)

        
class TestBase(unittest.TestCase):
    def tearDown(self):
        close_logging()
        for f in ['test.log', 'test.log.1']:
            if os.path.exists(f):
                os.remove(f)

    def setUp(self):
        # some of the base code may call the logger
        initialize_logging('test.log', interactive=True)
            
    def test_base(self):
        expected = [1, 2, 3, 4, 5]
        sensor = DummySensor(expected)
        publisher = SensorPublisher(sensor, '1')
        validator = ValidationSubscriber(expected, self)
        publisher.subscribe(validator)
        scheduler = Scheduler()
        scheduler.schedule_periodic(publisher, 1)
        scheduler.run_forever()
        self.assertTrue(validator.completed)

    def test_schedule_sensor(self):
        expected = [1, 2, 3, 4, 5]
        sensor = DummySensor(expected)
        validator = ValidationSubscriber(expected, self)
        scheduler = Scheduler()
        scheduler.schedule_sensor_periodic(sensor, 1, 1, [validator])
        scheduler.run_forever()
        self.assertTrue(validator.completed)

    def test_nonzero_sample_time(self):
        """Sensor sample time is greater than the interval between samples!
        """
        expected = [1, 2, 3, 4, 5]
        sensor = DummySensor(expected, sample_time=2)
        validator = ValidationSubscriber(expected, self)
        scheduler = Scheduler()
        scheduler.schedule_sensor_periodic(sensor, 1, 1, [validator])
        scheduler.run_forever()
        self.assertTrue(validator.completed)
        
        
if __name__ == '__main__':
    unittest.main()
