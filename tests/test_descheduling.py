"""
Test that, when all downstream input things are disconnected, 
the schedule deschedules the OutputThing.
"""

import asyncio
import unittest
from thingflow.base import InputThing, SensorAsOutputThing, Scheduler

from utils import RandomSensor


class PrintAndDeschedule(InputThing):
    def __init__(self, prev_in_chain, num_events=5):
        self.disconnect = prev_in_chain.connect(self)
        self.num_events = num_events
        self.prev_in_chain = prev_in_chain
        self.count = 0

    def on_next(self, x):
        print(x)
        self.count+=1
        if self.count==self.num_events:
            print("Disconnecting from sensor")
            self.disconnect()
            print(self.prev_in_chain.__connections__)

    def on_completed(self):
        print("on_completed")

    def on_error(self, e):
        print("on_error(%s)" % e)
        
class TestDescheduling(unittest.TestCase):
    def test_recurring(self):
        s = SensorAsOutputThing(RandomSensor(1))
        PrintAndDeschedule(s)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_recurring(s)
        scheduler.run_forever()
        print("Exited successfully")


    def test_periodic(self):
        s = SensorAsOutputThing(RandomSensor(1))
        PrintAndDeschedule(s)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(s, 0.25)
        scheduler.run_forever()
        print("Exited successfully")
        
if __name__ == '__main__':
    unittest.main()

        
