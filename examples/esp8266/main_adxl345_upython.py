"""For AntEvents MicroPython port, running on Feather Huzzah (ESP8266)

Script used on the ESP8266 to collect ADXL345 (accelerometer) data and send it
to an MQTT broker.

To use it, the parameters in the file need to be set (WIFI_SID, WIFI_PW, BROKER) and
the file renamed to 'main.py' which will be run when the ESP8266 is booted. Mpfshell
is recommended for transferring MicroPython files to the ESP8266.

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
