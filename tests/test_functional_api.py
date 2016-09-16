# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Tests for the functional-style api
"""
import asyncio
import unittest
import sys

from utils import ValueListSensor, ValidationSubscriber

from antevents.base import Scheduler, SensorPub
from antevents.linq.output import output
from antevents.linq.select import map
from antevents.linq.where import where
from antevents.linq.combinators import passthrough, compose

lux_data = [100, 200, 300, 450, 100, 200, 600]


class TestFunctionalApi(unittest.TestCase):
    """These are tests of the various features of the
    functional-style API. We want to make certain they
    work as advertised.
    """
    def test_complex_workflow(self):
        THRESHOLD = 300
        lux = ValueListSensor('lux-1', lux_data)
        scheduler = Scheduler(asyncio.get_event_loop())
        vs1 = ValidationSubscriber(lux_data, self)
        vs2 = ValidationSubscriber([False, False, False, True, False, False, True],
                                   self,
                                   extract_value_fn=lambda v: v)
        scheduler.schedule_sensor(lux, 0.5,
                                  passthrough(output()),
                                  passthrough(vs1),
                                  map(lambda event:event.val > THRESHOLD),
                                  passthrough(lambda v: print('ON' if v else 'OFF')),
                                  vs2, print_downstream=True)
        scheduler.run_forever()
        self.assertTrue(vs1.completed)
        self.assertTrue(vs2.completed)
        print("That's all folks")

    def test_thunk_builder_handling(self):
        """We have logic where we can pass a thunk builder into a combinator and
        it will do the right thing. Check that it works"""
        scheduler = Scheduler(asyncio.get_event_loop())
        lux = ValueListSensor('lux-2', lux_data)
        vs = ValidationSubscriber(lux_data, self)
        scheduler.schedule_sensor(lux, 0.5,
                                  passthrough(output()), # output() evaluates to a thunk
                                  passthrough(output), # output is a thunk builder
                                  passthrough(output(sys.stdout)), # output can take an arg
                                  vs, print_downstream=True)
        scheduler.run_forever()
        self.assertTrue(vs.completed)

    def test_passthrough_as_a_method(self):
        """Verify that, when passthrough is used as a method, it can still take
        thunks.
        """
        scheduler = Scheduler(asyncio.get_event_loop())
        luxpub = SensorPub(ValueListSensor('lux-2', lux_data))
        vs1 = ValidationSubscriber([450, 600], self)
        vs2 = ValidationSubscriber(lux_data, self)
        luxpub.passthrough(compose(where(lambda evt: evt.val>300), vs1)).subscribe(vs2)
        scheduler.schedule_periodic(luxpub, 0.5)
        scheduler.run_forever()
        self.assertTrue(vs1.completed)
        self.assertTrue(vs2.completed)
        
if __name__ == '__main__':
    unittest.main()

