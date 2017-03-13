# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Run a subscriber that blocks in its send call. It gets a separate dedicated thread.
"""

import unittest
import asyncio
import time
from thingflow.base import BlockingInputThing, Scheduler
from utils import make_test_output_thing_from_vallist

values = [ 1, 2, 3, 4, 5 ]

class TestInputThing(BlockingInputThing):
    def __init__(self, scheduler, expected_sequence, test_case):
        self.tc = test_case
        self.expected_sequence = expected_sequence
        self.idx = 0
        self.completed = False
        super().__init__(scheduler)

    def _on_next(self, port, x):
        assert port=='default'
        print("TestInputThing._on_next(%s)" % x.__repr__())
        self.tc.assertTrue(self.idx < len(self.expected_sequence),
                           "Received an event %s, but already at end of expected sequence" %
                           x.__repr__())
        self.tc.assertEqual(self.expected_sequence[self.idx], x[2],
                            "Expected and actual values do not match for item %d" % self.idx)
        self.idx += 1

    def _on_completed(self, port):
        assert port=='default'
        self.tc.assertEqual(len(self.expected_sequence), self.idx,
                            "Received on_completed when not at end of expected sequence")
        self.completed = True

    def _on_error(self, port, e):
        raise Exception("Should not get an on_error event. Got exception %s" % e)


class TestCase(unittest.TestCase):
    def test(self):
        scheduler = Scheduler(asyncio.get_event_loop())
        sensor = make_test_output_thing_from_vallist(1, values)
        scheduler.schedule_periodic(sensor, 1)
        blocking_subscriber = TestInputThing(scheduler, values, self)
        sensor.connect(blocking_subscriber)
        scheduler.run_forever()
        self.assertTrue(blocking_subscriber.completed)

if __name__ == '__main__':
    unittest.main()

        
                         
