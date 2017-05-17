# Make sure influxdb is running 

try:
    from influxdb import InfluxDBClient 
    from thingflow.adapters.influxdb import InfluxDBWriter,\
                                            InfluxDBReader
    PREREQS_AVAILABLE=True
except ImportError:
    PREREQS_AVAILABLE = False

try:
    from config_for_tests import INFLUXDB_USER, INFLUXDB_PASSWORD
except ImportError:
    INFLUXDB_USER=None
    INFLUXDB_PASSWORD=None
try:
    from config_for_tests import INFLUXDB_DATABASE
except ImportError:
    INFLUXDB_DATABASE='thingflow' # the default

import asyncio
import datetime, time
from collections import namedtuple
import unittest

from utils import ValueListSensor
from thingflow.base import Scheduler, SensorAsOutputThing, \
    SensorEvent, CallableAsInputThing



Sensor = namedtuple('Sensor', ['series_name', 'fields', 'tags'])

value_stream = [10, 13, 20, 20, 19, 19, 20, 21, 28, 28, 23, 21, 21, 18, 19, 16, 21,
                10, 13, 20, 20, 19, 19, 20, 21, 28, 28, 23, 21, 21, 18, 19, 16, 21]
value_stream2 = [2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6]

@unittest.skipUnless(PREREQS_AVAILABLE,
                     "influxdb client library not installed")
@unittest.skipUnless(INFLUXDB_USER is not None,
                     "Influxdb not configured in config_for_tests.py")
class TestInflux(unittest.TestCase):
    def test_influx_output(self):
        loop = asyncio.get_event_loop()
        s = ValueListSensor(1, value_stream)
        p = SensorAsOutputThing(s)
        b = InfluxDBWriter(msg_format=Sensor(series_name='Sensor', fields=['val', 'ts'], tags=['sensor_id']),
                           generate_timestamp=False,
                           username=INFLUXDB_USER,
                           password=INFLUXDB_PASSWORD,
                           database=INFLUXDB_DATABASE)
        p.connect(b)

        scheduler = Scheduler(loop)
        scheduler.schedule_periodic(p, 0.2) # sample five times every second
        scheduler.run_forever()

        # Now play back
        rs = self.c.query('SELECT * FROM Sensor;').get_points()
        for d in rs: 
            print(d)

        # Play back using an output thing
        p = InfluxDBReader('SELECT * FROM Sensor;',
                           database=INFLUXDB_DATABASE,
                           username=INFLUXDB_USER,
                           password=INFLUXDB_PASSWORD)
        p.connect(CallableAsInputThing(print))

        scheduler = Scheduler(loop)
        scheduler.schedule_periodic(p, 0.2) # sample five times every second
        scheduler.run_forever()
        print("That's all folks")

    def setUp(self):
        self.c = InfluxDBClient(database=INFLUXDB_DATABASE,
                                username=INFLUXDB_USER,
                                password=INFLUXDB_PASSWORD)
        self.c.delete_series(measurement='Sensor')
        #self.c.query('DELETE from Sensor;')
        
    def tearDown(self):
        self.c.delete_series(measurement='Sensor')
        #self.c.query('DELETE from Sensor;')
        
        
if __name__ == '__main__':
    unittest.main()
