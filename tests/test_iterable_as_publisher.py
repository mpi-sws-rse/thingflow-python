# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Test of IterableAsPublisher. This was originally test_base.py, but we then
added the sensor infrastructure and rewrote the test. This test verfies the
specific IterableAsPublisher code.
"""

import asyncio
import unittest

from antevents.base import Scheduler
from utils import make_test_publisher_from_vallist, ValidationSubscriber
import antevents.linq.where
import antevents.linq.output

value_stream = [
    20,
    30,
    100,
    120,
    20,
    5,
    2222
]

expected_stream = [
    100,
    120,
    2222
]

def predicate(v):
    if v[2]>=100.0:
        print("v=%s, True" % v[2])
        return True
    else:
        print("v=%s, False" % v[2])
        return False

class TestIterableAsPublisher(unittest.TestCase):
    def test_where(self):
        s = make_test_publisher_from_vallist(1, value_stream)
        w = s.where(predicate)
        w.output()
        vo = ValidationSubscriber(expected_stream, self)
        w.subscribe(vo)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(s, 0.5) # sample twice every second
        s.print_downstream()
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")
        self.assertTrue(vo.completed)
        print("That's all folks")


if __name__ == '__main__':
    unittest.main()

