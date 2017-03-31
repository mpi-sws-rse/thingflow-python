# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""These tests are designed to be run on a desktop. You can use
them to validate the system before deploying to 8266. They use stub
sensors.

Test end-to-end functionality where we sample a sensor event and write to a
queue. This only works if you have a broker at localhost:1883.

To validate that the messages are being received, go to the commandline and
run:
  mosquitto_sub -t test
"""

MQTT_PORT=1883

import sys
import os
import os.path
import time

try:
    from thingflow import *
except ImportError:
    sys.path.append(os.path.abspath('../'))
    from thingflow import *


import unittest

from mqtt_writer import MQTTWriter

class DummySensor(object):
    def __init__(self, sensor_id, value_stream, sample_time=0):
        self.sensor_id = sensor_id
        self.value_stream = value_stream
        self.idx = 0
        self.sample_time = sample_time

    def sample(self):
        if self.idx==len(self.value_stream):
            raise StopIteration()
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

class ValidationInputThing:
    """Compare the values in a event stream to the expected values.
    Use the test_case for the assertions (for proper error reporting in a unit
    test).
    """
    def __init__(self, expected_stream, test_case,
                 extract_value_fn=lambda event:event[2]):
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


def is_broker_running():
    import subprocess
    rc = subprocess.call("netstat -an | grep %d" % MQTT_PORT, shell=True)
    if rc==0:
        return True
    else:
        return False


@unittest.skipUnless(is_broker_running(),
                     "Did not find a broker listening on port %d" % MQTT_PORT)
class TestEndToEnd(unittest.TestCase):           
    def test_publish_sensor(self):
        expected = [1, 2, 3, 4, 5]
        sensor = DummySensor('lux-1', expected)
        output_thing = SensorAsOutputThing(sensor)
        validator = ValidationInputThing(expected, self)
        output_thing.connect(validator)
        self.writer = MQTTWriter('thingflow', 'localhost', MQTT_PORT, 'test')
        output_thing.connect(self.writer)
        scheduler = Scheduler()
        scheduler.schedule_periodic(output_thing, 1)
        scheduler.run_forever()
        self.assertTrue(validator.completed)        
        
if __name__ == '__main__':
    unittest.main()
