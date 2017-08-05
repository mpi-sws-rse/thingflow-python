# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Test of IterableAsOutputThing. This was originally test_base.py, but we then
added the sensor infrastructure and rewrote the test. This test verfies the
specific IterableAsOutputThing code.
"""

import asyncio
import unittest

from thingflow.base import Scheduler, IterableAsOutputThing
from utils import make_test_output_thing_from_vallist, ValidationInputThing
import thingflow.filters.where
import thingflow.filters.output

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

class ErrorIterator:
    """An iterator that thows an error after the initial stream
    (instead of StopIteration).
    """
    def __init__(self, expected_stream):
        self.expected_stream = expected_stream
        self.idx = 0

    def __iterator__(self):
        return self

    def __next__(self):
        if self.idx==len(self.expected_stream):
            raise Exception("Throwing an exception in ErrorIterator")
        else:
            v = self.expected_stream[self.idx]
            self.idx += 1
            return v

        
class TestIterableAsOutputThing(unittest.TestCase):
    def test_where(self):
        s = make_test_output_thing_from_vallist(1, value_stream)
        w = s.where(predicate)
        w.output()
        vo = ValidationInputThing(expected_stream, self)
        w.connect(vo)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(s, 0.5) # sample twice every second
        s.print_downstream()
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")
        self.assertTrue(vo.completed)
        print("That's all folks")

    def test_error_handling(self):
        """This is a non-fatal error, so we should just print the error and
        exit cleanly without propagating the exception.
        """
        s = IterableAsOutputThing(ErrorIterator(expected_stream))
        s.output()
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(s, 0.5) # sample twice every second
        s.print_downstream()
        scheduler.run_forever()
        

if __name__ == '__main__':
    unittest.main()

