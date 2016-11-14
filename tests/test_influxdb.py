# Make sure influxdb is running 

import asyncio
import datetime, time
from collections import namedtuple

from utils import ValueListSensor
from antevents.base import Scheduler, SensorPub, SensorEvent, CallableAsSubscriber

from antevents.adapters.influxdb import InfluxDBWriter, InfluxDBReader
from influxdb import InfluxDBClient 


Sensor = namedtuple('Sensor', ['series_name', 'fields', 'tags'])

value_stream = [10, 13, 20, 20, 19, 19, 20, 21, 28, 28, 23, 21, 21, 18, 19, 16, 21,
                10, 13, 20, 20, 19, 19, 20, 21, 28, 28, 23, 21, 21, 18, 19, 16, 21]
value_stream2 = [2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6]

def test_influx_output():
    loop = asyncio.get_event_loop()
    s = ValueListSensor(1, value_stream)
    p = SensorPub(s)
    b = InfluxDBWriter(msg_format=Sensor(series_name='Sensor', fields=['val', 'ts'], tags=['sensor_id']), generate_timestamp=False)
    p.subscribe(b)
 
    scheduler = Scheduler(loop)
    scheduler.schedule_periodic(p, 0.2) # sample five times every second
    scheduler.run_forever()

    # Now play back
    c = InfluxDBClient(database='antevents')
    rs = c.query('SELECT * FROM Sensor;').get_points()
    for d in rs: 
        print(d)

    # Play back using a publisher
    p = InfluxDBReader('SELECT * FROM Sensor;')
    p.subscribe(CallableAsSubscriber(print))

    scheduler = Scheduler(loop)
    scheduler.schedule_periodic(p, 0.2) # sample five times every second
    scheduler.run_forever()
    print("That's all folks")
    
if __name__ == "__main__":
    test_influx_output()
