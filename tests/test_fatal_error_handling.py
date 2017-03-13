# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Test that a fatal error causes the scheduler to exit.
"""
from thingflow.base import *
from utils import make_test_output_thing

import sys
import asyncio
import unittest

class DieAfter(InputThing):
    def __init__(self, num_events):
        self.events_left = num_events

    def on_next(self, x):
        self.events_left -= 1
        if self.events_left == 0:
            print("throwing fatal error")
            raise FatalError("this is a fatal error")

class TestFatalErrorHandling(unittest.TestCase):
    def test_case(self):
        sensor = make_test_output_thing(1)
        sensor.connect(print)
        sensor2 = make_test_output_thing(2)
        sensor2.connect(print)
        s = Scheduler(asyncio.get_event_loop())
        s.schedule_periodic(sensor, 1)
        s.schedule_periodic(sensor2, 1)
        sensor.connect(DieAfter(4))
        sensor.print_downstream()
        try:
            s.run_forever()
        except FatalError:
            print("got to end with fatal error thrown as expected")
        else:
            self.assertFalse(1, "Did not get to a fatal error")

if __name__ == '__main__':
    unittest.main()
