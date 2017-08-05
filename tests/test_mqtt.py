# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Test mqtt broker

In addition to testing mqtt publish/subscribe functionality, this runs a
output_thing that has its own event loop.

To run the test, you will need the paho-mqtt client and the mosquitto broker.
You can get the client via:

    pip install paho-mqtt

On Debian-based linuxes, you can get the broker via:

    sudo apt-get install mosquitto

We assume that the broker is listening on localhost:1883.

"""

import unittest
import sys
import thingflow.filters.output
import thingflow.filters.json
import thingflow.filters.select
from thingflow.base import Scheduler, InputThing, SensorEvent, ScheduleError, ExcInDispatch
from thingflow.adapters.mqtt import MQTTReader, MQTTWriter
from utils import make_test_output_thing_from_vallist, ValidationInputThing

try:
    import paho.mqtt
    MQTT_CLIENT_AVAILABLE = True
except ImportError:
    MQTT_CLIENT_AVAILABLE = False

MQTT_PORT=1883
    
import asyncio

sensor_data = [1, 2, 3, 4, 5]

class StopLoopAfter(InputThing):
    def __init__(self, stop_after, cancel_thunk):
        self.events_left = stop_after
        self.cancel_thunk = cancel_thunk

    def on_next(self, x):
        self.events_left -= 1
        if self.events_left == 0:
            print("Requesting stop of event loop")
            self.cancel_thunk()

def mqtt_msg_to_unicode(m):
    v = (m.payload).decode("utf-8")
    return v


def is_broker_running():
    import subprocess
    rc = subprocess.call("netstat -an | grep %d" % MQTT_PORT, shell=True)
    if rc==0:
        print("MQTT broker running")
        return True
    else:
        print("MQTT broker not running")
        return False


@unittest.skipUnless(MQTT_CLIENT_AVAILABLE,
                     "MQTT client not installed for python at %s" % sys.executable)
@unittest.skipUnless(is_broker_running(),
                     "MQTT broker not running on port %d" % MQTT_PORT)
class TestCase(unittest.TestCase):
    def test_mqtt(self):
        loop = asyncio.get_event_loop()
        s = Scheduler(loop)
        sensor = make_test_output_thing_from_vallist(1, sensor_data)
        mqtt_writer = MQTTWriter('localhost', topics=[('bogus/bogus',0),])
        sensor.to_json().connect(mqtt_writer)
        s.schedule_periodic(sensor, 0.5)

        mqtt_reader = MQTTReader("localhost", topics=[('bogus/bogus', 0),])
        vs = ValidationInputThing(sensor_data, self)
        mqtt_reader.take(5).select(mqtt_msg_to_unicode).from_json(constructor=SensorEvent) \
                       .output().connect(vs)
        c = s.schedule_on_private_event_loop(mqtt_reader)
        stop = StopLoopAfter(5, c)
        mqtt_reader.connect(stop)
        mqtt_reader.print_downstream()
        sensor.print_downstream()
        s.run_forever()
        loop.stop()
        self.assertTrue(vs.completed)
        print("that's it")

    def test_daniels_bug(self):
        """Test bug reported by Daniel (issue #1). If you call the mqtt writer without
        serializing the message, you should get a fatal error.
        """
        import time
        import asyncio
        import thingflow.filters.output  # This has output side-effect
        from thingflow.base import Scheduler, from_list
        from thingflow.adapters.mqtt import MQTTReader, MQTTWriter
        from collections import namedtuple

        StripEvent = namedtuple('StripEvent', ['strip_id', 'ts', 'val'])

        strip_events = (
            StripEvent('strip-1', 1500000000, 50),
            StripEvent('strip-1', 1500000000, 5),
            StripEvent('strip-1', 1500000000, 50))

        mqtt = MQTTWriter('localhost', topics=[('strip-data', 0),])

        strip = from_list(strip_events)
        strip.connect(mqtt)
        strip.output()

        sched = Scheduler(asyncio.get_event_loop())
        sched.schedule_periodic(strip, 1.0)
        try:
            sched.run_forever()
        except ScheduleError as e:
            # verify the cause of the error
            dispatch_error = e.__cause__
            self.assertTrue(isinstance(dispatch_error, ExcInDispatch),
                            "expecting cause to be a dispatch error, instead got %s" % repr(dispatch_error))
            orig_error = dispatch_error.__cause__
            self.assertTrue(isinstance(orig_error, TypeError),
                            "expecting original exception to be a TypeError, intead got %s" % repr(orig_error))
            print("Got expected exception: '%s'" % e)

if __name__ == '__main__':
    unittest.main()
