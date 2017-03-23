# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Sensors for AntEvents
Uses the nanpy library (https://github.com/nanpy/nanpy), which controls
a slave Arduino processor. The sensors are connected to the Arduino.

Both digital (1/0 output) and analogue (0-1023 ouput) sensors may be
be connected to the Arduino. To use this, Nanpy firmware needs to be
flashed onto the Arduino to allow Python to be used.

Note -This sensor class can only be used with sensors which send their output
straight to the  Arduino pins. For sensors which use I2C or SPI, with their
own registers, a library to use them has to be written separately.
"""

from thingflow.base import OutputThing, IndirectOutputThingMixin


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
