"""These tests are designed to be run on a desktop. You can use
them to validate the system before deploying to 8266. They use stub
sensors.

Test the scheduler's internal api.
"""

import sys
import os
import os.path

try:
    from antevents import *
except ImportError:
    sys.path.append(os.path.abspath('../'))
    from antevents import *


import unittest


class TestSensor(object):
    def __init__(self, initial_val):
        self.val = initial_val

    def get(self):
        return self.val

    
class TestScheduler(unittest.TestCase):
    def test_simple(self):
        sched = Scheduler()
        sched._add_task(1, 30)
        sched._add_task(2, 60)
        sched._add_task(3, 24)
        samples = sched._get_tasks_to_run()
        self.assertEqual(samples, [3, 1, 2])
        sleep = sched._get_next_sleep_interval()
        self.assertEqual(sleep, 24)
        sched._advance_time(24)
        samples = sched._get_tasks_to_run()
        self.assertEqual(samples, [3])
        sleep = sched._get_next_sleep_interval()
        self.assertEqual(sleep, 6)
        sched._advance_time(6)
        samples = sched._get_tasks_to_run()
        self.assertEqual(samples, [1])
        sleep = sched._get_next_sleep_interval()
        self.assertEqual(sleep, 18)
        sched._advance_time(18)
        samples = sched._get_tasks_to_run()
        self.assertEqual(samples, [3])
        sleep = sched._get_next_sleep_interval()
        self.assertEqual(sleep, 12)
        sched._advance_time(12)
        samples = sched._get_tasks_to_run()
        self.assertEqual(samples, [1, 2])

    def test_nonzero_sample_time(self):
        sched = Scheduler()
        sched._add_task(1, 30)
        sched._add_task(2, 60)
        samples = sched._get_tasks_to_run()
        self.assertEqual(samples, [1, 2])
        sched._advance_time(4)
        sleep = sched._get_next_sleep_interval()
        self.assertEqual(sleep, 26)
        sched._advance_time(28)
        samples = sched._get_tasks_to_run()
        self.assertEqual(samples, [1])
        sched._advance_time(1)
        sleep = sched._get_next_sleep_interval()
        self.assertEqual(sleep, 27)
        sched._advance_time(27)
        samples = sched._get_tasks_to_run()
        self.assertEqual(samples, [1, 2])

    def test_clock_wrap(self):
        sched = Scheduler(clock_wrap=64)
        sched._add_task(1, 8)
        sched._add_task(2, 16)
        for i in range(20):
            samples = sched._get_tasks_to_run()
            if (i%2)==0:
                self.assertEqual(samples, [1, 2])
            else:
                self.assertEqual(samples, [1])
            sleep = sched._get_next_sleep_interval()
            self.assertEqual(sleep, 8,
                             "sleep was %d instead of 8 for iteration %d" % (sleep, i))
            sched._advance_time(8)
                
    def test_overdue_clock_wrap(self):
        sched = Scheduler(clock_wrap=32)
        sched._add_task(1, 8)
        for i in range(10):
            samples = sched._get_tasks_to_run()
            self.assertEqual(samples,[1])
            sleep = sched._get_next_sleep_interval()
            if i==0:
                self.assertEqual(sleep, 8)
            else:
                self.assertEqual(sleep, 6)
            sched._advance_time(sleep+2) # go 2 seconds overdue
            
    def test__add_task_after_start(self):
        sched = Scheduler()
        sched._add_task(1, 4)
        sched._add_task(2, 8)
        for i in range(4):
            samples = sched._get_tasks_to_run()
            if (i%2)==0:
                self.assertEqual(samples, [1, 2])
            else:
                self.assertEqual(samples, [1])
            sleep = sched._get_next_sleep_interval()
            sched._advance_time(sleep)
        sched._add_task(3, 4)
        for i in range(4):
            samples = sched._get_tasks_to_run()
            if (i%2)==0:
                # order is based on creation order of intervals
                self.assertEqual(samples, [1, 3, 2])
            else:
                self.assertEqual(samples, [1, 3])
            sleep = sched._get_next_sleep_interval()
            sched._advance_time(sleep)

    def test__remove_task(self):
        sched = Scheduler()
        sched._add_task(1, 4)
        sched._add_task(2, 8)
        for i in range(4):
            samples = sched._get_tasks_to_run()
            if (i%2)==0:
                self.assertEqual(samples, [1, 2])
            else:
                self.assertEqual(samples, [1])
            sleep = sched._get_next_sleep_interval()
            sched._advance_time(sleep)
        sched._remove_task(1)
        for i in range(4):
            samples = sched._get_tasks_to_run()
            self.assertEqual(samples, [2])
            sleep = sched._get_next_sleep_interval()
            sched._advance_time(sleep)

    def test_noninteger_sensor(self):
        """So far, we've tested where we are passing interger sensor ids. We
        can also pass objects
        """
        s1 = TestSensor(1)
        s2 = TestSensor(2)
        sched = Scheduler()
        sched._add_task(s1, 4)
        sched._add_task(s2, 8)
        for i in range(4):
            samples = sched._get_tasks_to_run()
            if (i%2)==0:
                self.assertEqual(samples, [s1, s2])
            else:
                self.assertEqual(samples, [s1])
            sleep = sched._get_next_sleep_interval()
            sched._advance_time(sleep)
        sched._remove_task(s1)
        for i in range(4):
            samples = sched._get_tasks_to_run()
            self.assertEqual(samples, [s2])
            sleep = sched._get_next_sleep_interval()
            sched._advance_time(sleep)
        
        
if __name__ == '__main__':
    unittest.main()
