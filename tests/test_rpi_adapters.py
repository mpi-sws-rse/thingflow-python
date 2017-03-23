"""
Tests of RPI-specific functionality (adapters and sensors).
"""

import asyncio
import unittest
import platform

from utils import ValueListSensor
from thingflow.base import Scheduler, SensorAsOutputThing
import thingflow.filters.map
from thingflow.filters.output import output
from thingflow.filters.combinators import passthrough

MACHINE=platform.machine()

values = [
    0,
    1,
    0,
    1,
    0,
    1,
    0
]

@unittest.skipUnless(MACHINE=="armv7l",
                     "Tests are specific to RaspberryPi")
class TestRpi(unittest.TestCase):
    def test_gpio(self):
        import thingflow.adapters.rpi.gpio
        o = thingflow.adapters.rpi.gpio.GpioPinOut()
        sensor_thing = SensorAsOutputThing(ValueListSensor("sensor-1", values))
        sensor_thing.map(lambda evt: evt.val>0).passthrough(output()).connect(o)
        s = Scheduler(asyncio.get_event_loop())
        s.schedule_periodic(sensor_thing, 1.0)
        s.run_forever()



if __name__ == '__main__':
    unittest.main()

    
