"""This runs in Micropython on the esp8266. It samples the
lux sensor and pushes to an mqtt queue.
"""
from antevents import Scheduler 
from tsl2591 import Tsl2591
from mqtt_writer import MQTTWriter
from wifi import wifi_connect
import os

# Params to set
WIFI_SID=""
WIFI_PW=""
SENSOR_ID="front-room"
BROKER='192.168.11.153'

wifi_connect(WIFI_SID, WIFI_PW)
sensor = Tsl2591()
writer = MQTTWriter(SENSOR_ID, BROKER, 1883, 'remote-sensors')
sched = Scheduler()
sched.schedule_sensor(sensor, SENSOR_ID, 60, writer)
try:
  os.stat('stop-sampling.txt')
  print("Saw stop-sampling.txt, will skip rest")
except:
  print("Starting sensor sampling")
  sched.run_forever()

