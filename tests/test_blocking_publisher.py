"""Run an publisher that might block in a separate background thread
"""
import time
import unittest

from antevents.base import Publisher, DirectPublisherMixin, DefaultSubscriber,\
    Scheduler
from antevents.linq.combinators import passthrough
from antevents.linq.output import output
from utils import ValidationSubscriber

import asyncio

EVENTS = 4


class BlockingPublisher(Publisher, DirectPublisherMixin):
    def __init__(self):
        super().__init__()
        self.event_count = 0

    def _observe(self):
        self.event_count += 1
        time.sleep(0.5) # simulate a blocking call
        self._dispatch_next(self.event_count)
        

class StopLoopAfter(DefaultSubscriber):
    def __init__(self, stop_after, cancel_thunk):
        self.events_left = stop_after
        self.cancel_thunk = cancel_thunk

    def on_next(self, x):
        self.events_left -= 1
        if self.events_left == 0:
            print("Requesting stop of event loop")
            self.cancel_thunk()

class BlockingSensor:
    def __init__(self, sensor_id, stop_after):
        self.sensor_id = sensor_id
        self.stop_after = stop_after
        self.event_count = 0

    def sample(self):
        if self.event_count==self.stop_after:
            raise StopIteration
        self.event_count += 1
        time.sleep(0.5) # simulate a blocking call
        return self.event_count

    def __repr__(self):
        return "BlockingSensor(%s, stop_after=%s)" % (self.sensor_id,
                                                      self.stop_after)


class TestCase(unittest.TestCase):
    def test_blocking_publisher(self):
        o = BlockingPublisher()
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

    def test_blocking_sensor(self):
        s = BlockingSensor(1, stop_after=EVENTS)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_sensor_on_separate_thread(s, 1,
            passthrough(output()),
            ValidationSubscriber([i+1 for i in range(EVENTS)], self,
                                 extract_value_fn=lambda v:v),
            make_event_fn=lambda s, v: v)
        scheduler.run_forever()
        print("that's it")
        
if __name__ == '__main__':
    unittest.main()
        
