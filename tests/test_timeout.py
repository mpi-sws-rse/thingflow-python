# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Verify that we can set up timeout events
"""
import asyncio
import unittest
from thingflow.base import Scheduler, FunctionFilter
import thingflow.filters.timeout
import thingflow.filters.output
from utils import make_test_output_thing_from_vallist, ValidationInputThing

def on_next_alternate(self, x):
    if self.keep_mode:
        print("Sending %s" % x.__repr__())
        self._dispatch_next(x)
    else:
        print("Dropping %s" % x.__repr__())
    self.countdown -= 1
    if self.countdown==0:
        self.countdown = self.N
        self.keep_mode = not self.keep_mode

class DropPeriodic(FunctionFilter):
    """Allow through N events, drop the next N, and then repeat.
    """
    def __init__(self, previous_in_chain, N=1):
        self.N = N
        self.countdown = N
        self.keep_mode = True
        super().__init__(previous_in_chain, on_next=on_next_alternate,
                         name='drop_alternate')


class EventWatcher(thingflow.filters.timeout.EventWatcher):
    """Repeat the last good event
    """
    def __init__(self):
        self.last_good_event = None
    def on_next(self, x):
        self.last_good_event = x
    def produce_event_for_timeout(self):
        print("producing event for timeout: %s" %
              self.last_good_event.__repr__())
        return self.last_good_event

sensor_values = [
    1,
    2,
    3,
    4,
    5,
    6
]

expected_values = [
    1,
    1,
    3,
    3,
    5,
    5
]

expected_values_multiple_timeouts = [
    1,
    2,
    2,
    2,
    5,
    6
]

class TestTimeouts(unittest.TestCase):
    def test_supplying_event_on_timeout(self):
        """In this testcase, we drop every other event.
        We set the timeout to a bit longer than the event interval of
        one second. It then supplies the previous event. The resulting
        output stream will show every other value repeated twice.
        """
        sensor = make_test_output_thing_from_vallist(1, sensor_values)
        drop = DropPeriodic(sensor)
        scheduler = Scheduler(asyncio.get_event_loop())
        vo = ValidationInputThing(expected_values, self)
        drop.supply_event_when_timeout(EventWatcher(),
                                       scheduler, 1.1).output().connect(vo)
        scheduler.schedule_periodic(sensor, 1)            
        sensor.print_downstream()
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")

    def test_multiple_timeouts(self):
        """In this testcase, we pass two events, drop two events, etc.
        We set the timeout to a bit longer than the event interval. The last
        good value is supplied when the timeout expires. Thus, we should see
        two good events, two repeats of the first event, two good events, etc.
        """
        sensor = make_test_output_thing_from_vallist(1, sensor_values)
        drop = DropPeriodic(sensor, N=2)
        scheduler = Scheduler(asyncio.get_event_loop())
        vo = ValidationInputThing(expected_values_multiple_timeouts, self)
        drop.supply_event_when_timeout(EventWatcher(),
                                       scheduler, 1.1).output().connect(vo)
        scheduler.schedule_periodic(sensor, 1)            
        sensor.print_downstream()
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")


if __name__ == '__main__':
    unittest.main()

