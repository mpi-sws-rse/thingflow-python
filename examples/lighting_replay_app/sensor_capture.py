"""Capture data from multiple light sensors and save to rolling csv files
"""
import time
import asyncio
import sys

from antevents.base import Publisher, Scheduler
from antevents.sensor import SensorEvent
import antevents.adapters.csv
from antevents.adapters.csv import RollingCsvWriter
import antevents.linq.output
import antevents.linq.dispatch
import antevents.linq.select
import antevents.linq.json
from antevents.adapters.mqtt import MQTTReader

if len(sys.argv)>1:
    DIRECTORY=sys.argv[1]
else:
    DIRECTORY='.'
print("Using %s as directory for log files" % DIRECTORY)

LOCAL_SENSOR_ID='dining-room'
try:
    import tsl2591
    from antevents.adapters.rpi.lux_sensor import LuxSensor    
    HAS_LOCAL_SENSOR = True
except ImportError:
    HAS_LOCAL_SENSOR = False
    print("Warning: did not find tsl2591 library, cannot read directly connected sensors")

# Sensor ids for the remote sensors. Used to dispatch.
REMOTE_SENSORS = ['front-room', 'back-room']
def create_dispatch_rule(sensor_id):
    return (lambda evt:evt.sensor_id==sensor_id, sensor_id)
dispatch_rules = [create_dispatch_rule(remote_id) for remote_id in REMOTE_SENSORS]


scheduler = Scheduler(asyncio.get_event_loop())


if HAS_LOCAL_SENSOR:
    sensor = LuxSensor(sensor_id=LOCAL_SENSOR_ID)
    sensor.rolling_csv_writer(DIRECTORY, LOCAL_SENSOR_ID)
    sensor.output()
    scheduler.schedule_periodic_on_separate_thread(sensor, 60)

mqtt_reader = MQTTReader('localhost', client_id='rpi', topics=[('remote-sensors',0),])
# we convert the tuple received into a SensorEvent, overwriting the timestamp.
dispatcher = mqtt_reader.map(lambda m:(m.payload).decode("utf-8"))\
                        .from_json()\
                        .map(lambda tpl: SensorEvent(sensor_id=tpl[0], ts=time.time(), val=tpl[2]))\
                        .dispatch(dispatch_rules)
# For each remote sensor, we create a separate csv writer
for remote in REMOTE_SENSORS:
    dispatcher.rolling_csv_writer(DIRECTORY, remote, sub_topic=remote).output()
dispatcher.subscribe(lambda x: print("Unexpected sensor %s, full event was %s" %
                                     (x.sensor_id, x)))
#mqtt_reader.output()
mqtt_reader.print_downstream()

scheduler.schedule_on_private_event_loop(mqtt_reader)
print("Starting run...")
scheduler.run_forever()
