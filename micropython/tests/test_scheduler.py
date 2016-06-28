"""These tests are designed to be run on a desktop. You can use
them to validate the system before deploying to 8266. They use stub
sensors.

Test the scheduler.
"""

import sys
import os
import os.path

try:
    import antevents_upython
except ImportError:
    sys.path.append(os.path.abspath('../'))
    import antevents_upython

import unittest

from antevents_upython.scheduler import *

class TestSensor(object):
    def __init__(self, initial_val):
        self.val = initial_val

    def get(self):
        return self.val

    
class TestScheduler(unittest.TestCase):
    def test_find_interval_to_synchronize(self):
        existing = [7, 10, 15]
        i = find_interval_to_synchronize(5, existing)
        self.assertEqual(i, 10)
        i = find_interval_to_synchronize(20, existing)
        self.assertEqual(i, 10)
        i = find_interval_to_synchronize(17, existing)
        self.assertEqual(i, None)

    def test_simple(self):
        sched = Scheduler()
        sched.add_sensor(1, 30)
        sched.add_sensor(2, 60)
        sched.add_sensor(3, 24)
        samples = sched.get_sensors_to_sample()
        self.assertEqual(samples, [1, 2, 3])
        sleep = sched.get_next_sleep_interval()
        self.assertEqual(sleep, 24)
        sched.advance_time(24)
        samples = sched.get_sensors_to_sample()
        self.assertEqual(samples, [3])
        sleep = sched.get_next_sleep_interval()
        self.assertEqual(sleep, 6)
        sched.advance_time(6)
        samples = sched.get_sensors_to_sample()
        self.assertEqual(samples, [1])
        sleep = sched.get_next_sleep_interval()
        self.assertEqual(sleep, 18)
        sched.advance_time(18)
        samples = sched.get_sensors_to_sample()
        self.assertEqual(samples, [3])
        sleep = sched.get_next_sleep_interval()
        self.assertEqual(sleep, 12)
        sched.advance_time(12)
        samples = sched.get_sensors_to_sample()
        self.assertEqual(samples, [1, 2])

    def test_nonzero_sample_time(self):
        sched = Scheduler()
        sched.add_sensor(1, 30)
        sched.add_sensor(2, 60)
        samples = sched.get_sensors_to_sample()
        self.assertEqual(samples, [1, 2])
        sched.advance_time(4)
        sleep = sched.get_next_sleep_interval()
        self.assertEqual(sleep, 26)
        sched.advance_time(28)
        samples = sched.get_sensors_to_sample()
        self.assertEqual(samples, [1])
        sched.advance_time(1)
        sleep = sched.get_next_sleep_interval()
        self.assertEqual(sleep, 27)
        sched.advance_time(27)
        samples = sched.get_sensors_to_sample()
        self.assertEqual(samples, [1, 2])

    def test_clock_wrap(self):
        sched = Scheduler(clock_wrap_interval=64)
        sched.add_sensor(1, 8)
        sched.add_sensor(2, 16)
        for i in range(20):
            samples = sched.get_sensors_to_sample()
            if (i%2)==0:
                self.assertEqual(samples, [1, 2])
            else:
                self.assertEqual(samples, [1])
            sleep = sched.get_next_sleep_interval()
            self.assertEqual(sleep, 8,
                             "sleep was %d instead of 8 for iteration %d" % (sleep, i))
            sched.advance_time(8)
                
    def test_overdue_clock_wrap(self):
        sched = Scheduler(clock_wrap_interval=32)
        sched.add_sensor(1, 8)
        for i in range(10):
            samples = sched.get_sensors_to_sample()
            self.assertEqual(samples,[1])
            sleep = sched.get_next_sleep_interval()
            if i==0:
                self.assertEqual(sleep, 8)
            else:
                self.assertEqual(sleep, 6)
            sched.advance_time(sleep+2) # go 2 seconds overdue
            
    def test_add_sensor_after_start(self):
        sched = Scheduler()
        sched.add_sensor(1, 4)
        sched.add_sensor(2, 8)
        for i in range(4):
            samples = sched.get_sensors_to_sample()
            if (i%2)==0:
                self.assertEqual(samples, [1, 2])
            else:
                self.assertEqual(samples, [1])
            sleep = sched.get_next_sleep_interval()
            sched.advance_time(sleep)
        sched.add_sensor(3, 4)
        for i in range(4):
            samples = sched.get_sensors_to_sample()
            if (i%2)==0:
                # order is based on creation order of intervals
                self.assertEqual(samples, [1, 3, 2])
            else:
                self.assertEqual(samples, [1, 3])
            sleep = sched.get_next_sleep_interval()
            sched.advance_time(sleep)

    def test_remove_sensor(self):
        sched = Scheduler()
        sched.add_sensor(1, 4)
        sched.add_sensor(2, 8)
        for i in range(4):
            samples = sched.get_sensors_to_sample()
            if (i%2)==0:
                self.assertEqual(samples, [1, 2])
            else:
                self.assertEqual(samples, [1])
            sleep = sched.get_next_sleep_interval()
            sched.advance_time(sleep)
        sched.remove_sensor(1)
        for i in range(4):
            samples = sched.get_sensors_to_sample()
            self.assertEqual(samples, [2])
            sleep = sched.get_next_sleep_interval()
            sched.advance_time(sleep)

    def test_noninteger_sensor(self):
        """So far, we've tested where we are passing interger sensor ids. We
        can also pass objects
        """
        s1 = TestSensor(1)
        s2 = TestSensor(2)
        sched = Scheduler()
        sched.add_sensor(s1, 4)
        sched.add_sensor(s2, 8)
        for i in range(4):
            samples = sched.get_sensors_to_sample()
            if (i%2)==0:
                self.assertEqual(samples, [s1, s2])
            else:
                self.assertEqual(samples, [s1])
            sleep = sched.get_next_sleep_interval()
            sched.advance_time(sleep)
        sched.remove_sensor(s1)
        for i in range(4):
            samples = sched.get_sensors_to_sample()
            self.assertEqual(samples, [s2])
            sleep = sched.get_next_sleep_interval()
            sched.advance_time(sleep)
        
        
if __name__ == '__main__':
    unittest.main()
