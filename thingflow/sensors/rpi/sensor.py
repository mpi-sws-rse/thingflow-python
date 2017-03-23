# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Sensors for ThingFlow
	Updated to suit the API changes Jeff mentioned, so that the following can be used as follows:
		sensor = SensorAsOutputThing(RPISensor())
	The following classes allow digital/analogue sensors (which are not connected using I2C) to be connected to a Raspberry Pi/Arduino and used with ThingFlow
"""

from thingflow.base import OutputThing, IndirectOutputThingMixin

import RPi.GPIO as GPIO
class RPISensor(OutputThing, IndirectOutputThingMixin):
    """Sensor connected to Raspberry Pi. Output of sensor is digital (RPi does not come with an ADC unlike the Arduino)
    """
    def __init__(self,sensor_id):
        """sensor_id is port number
        """
        super().__init__()
        self.sensor_id = sensor_id
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(sensor_id,GPIO.IN)

    def sample(self):
        val = GPIO.input(self.sensor_id)
        return val

    def __str__(self):
        return 'Raspberry Pi Sensor (port=%s)'% self.sensor_id


from nanpy import ArduinoApi,SerialManager
ardApi = ArduinoApi(connection=SerialManager(device = '/dev/ttyACM0'))

class ArduinoSensor(OutputThing, IndirectOutputThingMixin):
    """Sensor connected to Arduino. Output is analogue(1/0) or digital output(0 - 1023). Nanpy firmware needs to be flashed onto Arduino.
    """    
    def __init__(self,sensor_id,AD):
        """sensor_id is port number, AD is True/False for Analogue/Digital
        """
        super().__init__()
        self.sensor_id = sensor_id
        self.AD = AD
        ardApi.pinMode(sensor_id,ardApi.INPUT)
        
    def sample(self):
        if self.AD:
            val = ardApi.digitalRead(self.sensor_id)
        else:
            val = ardApi.analogRead(self.sensor_id)
        return val

    def __str__(self):
        return 'Arduino Sensor (port=%s, AD=%s)'% (self.sensor_id, self.AD)
