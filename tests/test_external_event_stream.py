# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Run an observable that has its own event loop.
We use the MQTT reader with the mock client to test this
(does not require an mqtt broker).
"""
import antevents.linq.output
from antevents.base import Scheduler, DefaultSubscriber
from antevents.adapters.mqtt import MQTTReader, MockMQTTClient

import unittest
import asyncio


class StopLoopAfter(DefaultSubscriber):
    def __init__(self, stop_after, cancel_thunk):
        self.events_left = stop_after
        self.cancel_thunk = cancel_thunk

    def on_next(self, x):
        self.events_left -= 1
        if self.events_left == 0:
            print("Requesting stop of event loop")
            self.cancel_thunk()

class TestExternalEventStream(unittest.TestCase):
    def test_case(self):
        """Just run the reader in its own event loop. We stop everything after 4
        events.
        """
        s = Scheduler(asyncio.get_event_loop())
        m = MQTTReader("localhost", topics=[('bogus/bogus', 0),],
                       mock_class=MockMQTTClient)
        m.output()
        c = s.schedule_on_private_event_loop(m)
        m.subscribe(StopLoopAfter(4, c))
        m.print_downstream()
        s.run_forever()
        print("that's it")


if __name__ == '__main__':
    unittest.main()
        
