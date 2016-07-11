"""Run an publisher that might block in a separate background thread
"""
import time
import unittest

import antevents.linq.output
from antevents.base import*
from utils import ValidationSubscriber

import asyncio

EVENTS = 4


class TestPublisher(Publisher, IndirectPublisherMixin):
    def __init__(self):
        super().__init__()
        self.event_count = 0

    def _observe_and_enqueue(self):
        self.event_count += 1
        time.sleep(0.5) # simulate a blocking call
        self._dispatch_next(self.event_count)
        return True

        

class StopLoopAfter(DefaultSubscriber):
    def __init__(self, stop_after, cancel_thunk):
        self.events_left = stop_after
        self.cancel_thunk = cancel_thunk

    def on_next(self, x):
        self.events_left -= 1
        if self.events_left == 0:
            print("Requesting stop of event loop")
            self.cancel_thunk()


class TestCase(unittest.TestCase):
    def test_blocking_publisher(self):
        o = TestPublisher()
        o.output()
        scheduler = Scheduler(asyncio.get_event_loop())
        c = scheduler.schedule_periodic_on_separate_thread(o, 1)
        vs = ValidationSubscriber([i+1 for i in range(EVENTS)], self,
                                  extract_value_fn=lambda v:v)
        o.subscribe(vs)
        o.subscribe(StopLoopAfter(EVENTS, c))
        o.print_downstream()
        scheduler.run_forever()
        print("that's it")

if __name__ == '__main__':
    unittest.main()
        
