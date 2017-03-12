# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Some simple tests for the base layer.
"""

import asyncio
import unittest

from thingflow.base import Scheduler, SensorAsOutputThing
from utils import ValueListSensor, ValidationInputThing
from thingflow.filters.where import where
from thingflow.filters.output import output
from thingflow.filters.combinators import passthrough

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


class TestBaseScenario(unittest.TestCase):
    def test_where(self):
        """In this version, we create a publisher and use method chaining to
        compose the filters"""
        s = ValueListSensor(1, value_stream)
        p = SensorAsOutputThing(s)
        w = p.where(predicate)
        w.output()
        vo = ValidationInputThing(expected_stream, self.test_where)
        w.connect(vo)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(p, 0.5) # sample twice every second
        p.print_downstream()
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")
        print("That's all folks")

    def test_schedule_sensor(self):
        """In this version, we pass the sensor directly to the scheduler and use
        a functional style to compose the filters"""
        s = ValueListSensor(1, value_stream)
        vo = ValidationInputThing(expected_stream, self.test_schedule_sensor)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_sensor(s, 0.5,
                                  where(predicate),
                                  passthrough(vo),
                                  output())
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")
        print("That's all folks")
        


if __name__ == '__main__':
    unittest.main()

