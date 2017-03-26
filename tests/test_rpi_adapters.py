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
from utils import StopAfterN

MACHINE=platform.machine()

# Check whether the library for tsl2591 is installed.
# See https://github.com/maxlklaxl/python-tsl2591.git
try:
    import tsl2591
    TSL2591_INSTALLED=True
except:
    TSL2591_INSTALLED=False

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
        
    @unittest.skipUnless(TSL2591_INSTALLED,
                         "TSL2591 sensor library not installed")
    def test_tsl2591(self):
        import thingflow.sensors.rpi.lux_sensor
        sensor = SensorAsOutputThing(thingflow.sensors.rpi.lux_sensor.LuxSensor())
        s = Scheduler(asyncio.get_event_loop())
        stop = s.schedule_periodic(sensor, 1.0)
        StopAfterN(sensor, stop, N=4).output()
        s.run_forever()
        



if __name__ == '__main__':
    unittest.main()

    
