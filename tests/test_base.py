# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Some simple tests for the base layer.
"""

import asyncio
import unittest

from thingflow.base import Scheduler, SensorAsOutputThing, FunctionFilter
from utils import ValueListSensor, ValidationInputThing, CaptureInputThing
from thingflow.filters.where import where
from thingflow.filters.output import output
from thingflow.filters.map import map
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


class TestFunctionFilter(unittest.TestCase):
    def test_function_filter(self):
        """Verify the function filter class
        """
        s = ValueListSensor(1, value_stream)
        st = SensorAsOutputThing(s)
        captured_list_ref = [[]]
        got_completed_ref = [False,]
        def on_next(self, x):
            captured_list_ref[0].append(x.val)
            self._dispatch_next(x)
        def on_completed(self):
            got_completed_ref[0] = True
            self._dispatch_completed()
        ff = FunctionFilter(st, on_next=on_next, on_completed=on_completed)
        vo = ValidationInputThing(value_stream, self.test_function_filter)
        ff.connect(vo)
        st.print_downstream()
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(st, 0.5) # sample twice every second
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")
        self.assertEqual(value_stream, captured_list_ref[0])
        self.assertTrue(got_completed_ref[0])
        print("That's all folks")

    def test_function_filter_error_handling(self):
        """Verify the error handling functionality of the function filter. We do
        this by connecting two downstream paths to the sensor. The first includes
        a function filter that throws an error when it encouters a sensor reading
        of 120. This should disconnect th stream at this point. The second is
        a normal validation input thing. It is connected directly to the sensor,
        and thus should not see any errors.
        """
        s = ValueListSensor(1, value_stream)
        st = SensorAsOutputThing(s)
        captured_list_ref = [[]]
        got_completed_ref = [False,]
        got_on_error_ref = [False,]
        def on_next_throw_exc(self, x):
            if x.val==120:
                raise Exception("expected exc")
            else:
                captured_list_ref[0].append(x.val)
                self._dispatch_next(x)
        def on_completed(self):
            got_completed_ref[0] = True
            self._dispatch_completed()
        def on_error(self, e):
            got_on_error_ref[0] = True
            self._dispatch_error(e)
        ff = FunctionFilter(st, on_next=on_next_throw_exc,
                            on_completed=on_completed,
                            on_error=on_error)
        ct = CaptureInputThing(expecting_error=True)
        ff.map(lambda x: x.val).connect(ct)
        vo = ValidationInputThing(value_stream, self.test_function_filter_error_handling)
        st.connect(vo)
        st.print_downstream()
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(st, 0.5) # sample twice every second
        scheduler.run_forever()
        self.assertTrue(vo.completed,
                        "Schedule exited before validation observer completed")
        self.assertFalse(ct.completed,
                         "Capture thing should not have completed")
        self.assertTrue(ct.errored,
                        "Capture thing should have seen an error")
        self.assertFalse(got_completed_ref[0])
        self.assertTrue(got_on_error_ref[0])
        self.assertEqual([20, 30, 100], ct.events, "Capture thing event mismatch")
        self.assertEqual([20, 30, 100], captured_list_ref[0], "captured_list_ref mismatch")
        print("That's all folks")
        

    

if __name__ == '__main__':
    unittest.main()

