# Copyright 2017 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Test async version of mqtt libraries. Depends on hbmqtt
(https://github.com/beerfactory/hbmqtt)

"""

import unittest
import sys
import asyncio
from antevents.base import Scheduler, SensorPub, SensorEvent
import antevents.linq.output
import antevents.linq.combinators
import antevents.linq.select
from antevents.adapters.mqtt_async import QueueWriter, QueueReader
from antevents.linq.transducer import PeriodicMedianTransducer
from utils import ValueListSensor, ValidateAndStopSubscriber


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
    6.5
]

EXPECTED = [
    2.5,
    4.1,
    6.5
]

def msg_to_event(msg):
    return SensorEvent(sensor_id=msg[0], ts=msg[1], val=msg[2])

    
@unittest.skipUnless(HBMQTT_AVAILABLE,
                     "HBMQTT library not installed for python at %s" %
                     sys.executable)
class TestCase(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.sched = Scheduler(self.loop)
    def tearDown(self):
        self.loop.stop()
        
    # def test_client_only(self):
    #     SENSOR_ID='sensor-1'
    #     sensor = SensorPub(ValueListSensor(SENSOR_ID, VALUES))
    #     td = sensor.transduce(PeriodicMedianTransducer(period=3))
    #     qw = QueueWriter(td, URL, SENSOR_ID, self.sched)
    #     qw.output()
    #     self.sched.schedule_periodic(sensor, 0.5)
    #     self.sched.run_forever()
    #     self.assertFalse(qw.has_pending_requests(),
    #                      "QueueWriter has pending requests: %s" % qw.dump_state())
    #     print("test_client_only completed")

    def test_client_and_server(self):
        SENSOR_ID='sensor-1'
        sensor = SensorPub(ValueListSensor(SENSOR_ID, VALUES))
        td = sensor.transduce(PeriodicMedianTransducer(period=3))
        qw = QueueWriter(td, URL, SENSOR_ID, self.sched)
        qw.output()
        qr = QueueReader(URL, SENSOR_ID, self.sched)
        self.sched.schedule_periodic(sensor, 0.5)
        stop_qr = self.sched.schedule_on_main_event_loop(qr)
        qr.select(msg_to_event).subscribe(ValidateAndStopSubscriber(EXPECTED, self, stop_qr))
        self.sched.run_forever()
        self.assertFalse(qw.has_pending_requests(),
                         "QueueWriter has pending requests: %s" % qw.dump_state())
        print("test_client_and_server completed")
        

if __name__ == '__main__':
    unittest.main()
    
