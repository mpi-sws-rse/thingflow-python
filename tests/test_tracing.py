"""Test that tracing works properly.
The automated test only verifies that tracing does not cause
a crash. You have to verify the actual messages manually
"""
import unittest
import asyncio
from thingflow.base import *
from utils import ValueListSensor, ValidationInputThing
from thingflow.filters.map import map
from thingflow.filters.output import output
from thingflow.filters.combinators import passthrough

values = [1,2,3,4,5]

class TestTracing(unittest.TestCase):
    def test_tracing(self):
        s = ValueListSensor(1, values)
        p = SensorAsOutputThing(s)
        v = ValidationInputThing([v+1 for v in values], self,
                                 extract_value_fn=lambda x:x)
        p.passthrough(output).map(lambda x : x.val+1).passthrough(output).connect(v)
        p.trace_downstream()
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(p, 0.5) # sample twice every second
        scheduler.run_forever()


if __name__ == '__main__':
    unittest.main()

