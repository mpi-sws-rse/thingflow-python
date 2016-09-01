"""Some simple tests for the base layer.
"""

import asyncio
import unittest

from antevents.base import Scheduler, SensorPub
from utils import ValueListSensor, ValidationSubscriber
from antevents.linq.where import where
from antevents.linq.output import output
from antevents.linq.combinators import passthrough

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
        p = SensorPub(s)
        w = p.where(predicate)
        w.output()
        vo = ValidationSubscriber(expected_stream, self)
        w.subscribe(vo)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(p, 0.5) # sample twice every second
        p.print_downstream()
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")
        self.assertTrue(vo.completed)
        print("That's all folks")

    def test_schedule_sensor(self):
        """In this version, we pass the sensor directly to the scheduler and use
        a functional style to compose the filters"""
        s = ValueListSensor(1, value_stream)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_sensor(s, 0.5,
                                  where(predicate),
                                  passthrough(ValidationSubscriber(expected_stream, self)),
                                  output())


if __name__ == '__main__':
    unittest.main()

