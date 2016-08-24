"""AntEvents MicroPython port, running on Feather Huzzah (ESP8266)
	Sampling an ADXL345 (accelerometer)
	Based on antevents-python/examples/lighting_replay_app/esp8266_main.py
	To use, rename to main.py and use mpfshell to load onto Feather Huzzah
	Also load the files for the AntEvents MicroPython port and adxl345_upy.py
"""
from antevents import Scheduler 
from adxl345_upy import ADXL345_upy
from mqtt_writer import MQTTWriter
from wifi import wifi_connect
import os

# Params to set
WIFI_SID=""
WIFI_PW=""
SENSOR_ID="accelerometer"
BROKER=''

wifi_connect(WIFI_SID, WIFI_PW)
sensor = ADXL345_upy(sensor_id=2)
writer = MQTTWriter(SENSOR_ID, BROKER, 1883, 'sensor/1')
sched = Scheduler()
frequency = 5 #Hz
sched.schedule_sensor(sensor, 1/frequency, writer)
try:
  os.stat('stop-sampling.txt')
  print("Saw stop-sampling.txt, will skip rest")
except:
  print("Starting sensor sampling")
  sched.run_forever()