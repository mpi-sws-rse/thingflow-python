# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Raspberry Pi GPIO Sensor for AntEvents.
Allows digital (1/0 output) sensors to be connected straight to the
Raspberry Pi (ADC needed for the Pi to take analogue output).

This sensor class can only be used with sensors which send their output straight
to the Raspberry Pi GPIO pins. For sensors which use I2C or SPI, with their
own registers, a library to use them has to be written separately.
"""

from thingflow.base import OutputThing, IndirectOutputThingMixin

import RPi.GPIO as GPIO
class RPISensor(OutputThing, IndirectOutputThingMixin):
    """Sensor connected to Raspberry Pi. Output of sensor is digital
    (RPi does not come with an ADC unlike the Arduino)
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

