"""Test mqtt broker
"""

"""Run an observable that has its own event loop.
"""
import unittest
import antevents.linq.output
import antevents.linq.json
import antevents.linq.select
from antevents.base import Scheduler, DefaultSubscriber, SensorEvent
from antevents.adapters.mqtt import MQTTReader, MQTTWriter
from utils import make_test_publisher_from_vallist, ValidationSubscriber

try:
    import paho.mqtt
    MQTT_CLIENT_AVAILABLE = True
except ImportError:
    MQTT_CLIENT_AVAILABLE = False

MQTT_PORT=1883
    
import asyncio

sensor_data = [1, 2, 3, 4, 5]

class StopLoopAfter(DefaultSubscriber):
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
        return True
    else:
        return False


@unittest.skipUnless(MQTT_CLIENT_AVAILABLE and is_broker_running(),
                     "MQTT client not installed or broker not running on port %d" %
                     MQTT_PORT)
class TestCase(unittest.TestCase):
    def test_mqtt(self):
        loop = asyncio.get_event_loop()
        s = Scheduler(loop)
        sensor = make_test_publisher_from_vallist(1, sensor_data)
        mqtt_writer = MQTTWriter('localhost', topics=[('bogus/bogus',0),])
        sensor.to_json().subscribe(mqtt_writer)
        s.schedule_periodic(sensor, 0.5)

        mqtt_reader = MQTTReader("localhost", topics=[('bogus/bogus', 0),])
        vs = ValidationSubscriber(sensor_data, self)
        mqtt_reader.take(5).select(mqtt_msg_to_unicode).from_json(constructor=SensorEvent) \
                       .output().subscribe(vs)
        c = s.schedule_on_private_event_loop(mqtt_reader)
        stop = StopLoopAfter(5, c)
        mqtt_reader.subscribe(stop)
        mqtt_reader.print_downstream()
        sensor.print_downstream()
        s.run_forever()
        loop.stop()
        self.assertTrue(vs.completed)
        print("that's it")

if __name__ == '__main__':
    unittest.main()
