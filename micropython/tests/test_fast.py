# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
This isn't actually a unit test - it is for validating fast sampling on the
actual ESP8266. It samples a dummy sensor at 10Hz and pushes to an
MQTT queue. To run it:

0. Set up an mqtt broker (mosquitto)
1. Replace the CHANGE_ME values with the appropriate values for your environment
2. Copy the script to the ESP8266 (e.g. via mpfsheel) and import the module.
"""
from antevents import Scheduler 
from mqtt_writer import MQTTWriter
from wifi import wifi_connect
import uos
import ustruct


# Params to set
WIFI_SID="CHANGE_ME"
WIFI_PW="CHANGE_ME"
SENSOR_ID="front-room"
BROKER='CHANGE_ME'

class DummySensor:
  def __init__(self, sensor_id):
    self.sensor_id = sensor_id

  def sample(self):
        return ustruct.unpack('@H', uos.urandom(2))[0]

  
wifi_connect(WIFI_SID, WIFI_PW)
sensor = DummySensor(sensor_id=SENSOR_ID)
writer = MQTTWriter(SENSOR_ID, BROKER, 1883, 'remote-sensors')
sched = Scheduler()
sched.schedule_sensor(sensor, 0.1, writer)
print("Starting sensor sampling")
sched.run_forever()

