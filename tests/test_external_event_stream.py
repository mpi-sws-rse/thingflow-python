"""Run an observable that has its own event loop.
"""
import antevents.linq.output
from antevents.base import Scheduler, DefaultSubscriber
from antevents.adapters.mqtt import MQTTReader, MockMQTTClient

import asyncio
s = Scheduler(asyncio.get_event_loop())

m = MQTTReader("localhost", topics=[('bogus/bogus', 0),],
               mock_class=MockMQTTClient)
m.output()

class StopLoopAfter(DefaultSubscriber):
    def __init__(self, stop_after, cancel_thunk):
        self.events_left = stop_after
        self.cancel_thunk = cancel_thunk

    def on_next(self, x):
        self.events_left -= 1
        if self.events_left == 0:
            print("Requesting stop of event loop")
            self.cancel_thunk()


c = s.schedule_on_private_event_loop(m)
m.subscribe(StopLoopAfter(4, c))
m.print_downstream()
s.run_forever()
print("that's it")
