"""Capture data from multiple light sensors and save to rolling csv files
"""
import asyncio
from antevents.base import Publisher, Scheduler
import antevents.adapters.csv
import antevents.linq.output
from antevents.adapters.rpi.lux_sensor import LuxSensor
from antevents.adapters.mqtt import MQTTReader

DIRECTORY='.'
LOCAL_SENSOR='dining-room'

sensor = LuxSensor()
sensor.rolling_csv_writer(DIRECTORY, LOCAL_SENSOR)
sensor.output()
mqtt_reader = MQTTReader('localhost', topics=['remote-sensors',])
mqtt_reader.rolling_csv_writer(DIRECTORY, 'front-room')
mqtt_reader.output()
scheduler = Scheduler(asyncio.get_event_loop())
scheduler.schedule_periodic_on_separate_thread(sensor, 60)
scheduler.schedule_on_private_event_loop(mqtt_reader)
print("Starting run...")
scheduler.run_forever()
