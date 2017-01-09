# Copyright 2017 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Test async version of mqtt libraries. Depends on hbmqtt
(https://github.com/beerfactory/hbmqtt)

"""

import unittest
import sys
import asyncio
import string
from random import choice, seed
from antevents.base import Scheduler, SensorPub, SensorEvent
import antevents.linq.output
import antevents.linq.combinators
import antevents.linq.select
from antevents.adapters.mqtt_async import QueueWriter, QueueReader
from antevents.linq.transducer import PeriodicMedianTransducer
from utils import ValueListSensor, ValidateAndStopSubscriber

seed()

try:
    import hbmqtt
    HBMQTT_AVAILABLE = True
except ImportError:
    HBMQTT_AVAILABLE = False

URL = "mqtt://localhost:1883"
    

VALUES = [
    1.0,
    2.5,
    3.7,
    4.1,
    8.1,
    0.5,
    6.5,
    4.5,
    3.9,
    6.5
]

EXPECTED = [
    2.5,
    4.1,
    4.5,
    6.5
]

def msg_to_event(msg):
    return SensorEvent(sensor_id=msg[0], ts=msg[1], val=msg[2])

CHARS=string.ascii_letters+string.digits
def get_topic_name(test_class):
    return  test_class.__class__.__name__ + ''.join([ choice(CHARS) for i in range(5) ])
    
@unittest.skipUnless(HBMQTT_AVAILABLE,
                     "HBMQTT library not installed for python at %s" %
                     sys.executable)
class TestCase(unittest.TestCase):
    def setUp(self):
        # Creating a new event loop each test case does not seem to work.
        # I think it is due to hbmqtt not cleaning up some state in the asyncio
        # layer.
        #self.loop = asyncio.new_event_loop()
        self.loop = asyncio.get_event_loop()
        self.sched = Scheduler(self.loop)
    def tearDown(self):
        pass
        #self.loop.stop()
        #self.loop.close()
        
    def test_client_only(self):
        SENSOR_ID='sensor-1'
        TOPIC=get_topic_name(self)
        sensor = SensorPub(ValueListSensor(SENSOR_ID, VALUES))
        td = sensor.transduce(PeriodicMedianTransducer(period=3))
        qw = QueueWriter(td, URL, TOPIC, self.sched)
        qw.output()
        self.sched.schedule_periodic(sensor, 0.5)
        self.sched.run_forever()
        self.assertFalse(qw.has_pending_requests(),
                         "QueueWriter has pending requests: %s" % qw.dump_state())
        print("test_client_only completed")

    def send_and_recv_body(self, sleep_timeout):
        SENSOR_ID='sensor-1'
        TOPIC=get_topic_name(self)
        sensor = SensorPub(ValueListSensor(SENSOR_ID, VALUES))
        td = sensor.transduce(PeriodicMedianTransducer(period=3))
        qw = QueueWriter(td, URL, TOPIC, self.sched)
        qw.output()
        qr = QueueReader(URL, TOPIC, self.sched, timeout=sleep_timeout)
        self.sched.schedule_periodic(sensor, 0.5)
        stop_qr = self.sched.schedule_on_main_event_loop(qr)
        vs = ValidateAndStopSubscriber(EXPECTED, self, stop_qr)
        qr.select(msg_to_event).subscribe(vs)
        self.sched.run_forever()
        self.assertFalse(qw.has_pending_requests(),
                         "QueueWriter has pending requests: %s" % qw.dump_state())
        self.assertEqual(qr.state, QueueReader.FINAL_STATE)
        self.assertEqual(vs.next_idx, len(EXPECTED))
        print("send_and_recv_bod(%s) completed" % sleep_timeout)

    def test_short_timeout(self):
        self.send_and_recv_body(0.1)

    def test_long_timeout(self):
        self.send_and_recv_body(3.0)
        

if __name__ == '__main__':
    unittest.main()
    
