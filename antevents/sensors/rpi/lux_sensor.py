# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
This is a sensor for the tsl2591 lux (light level) sensor breakout board
from Adafruit. It is a thin layer on top of python-tsl2591.
To install the tsl2591 library:
  sudo apt-get install build-essential libi2c-dev i2c-tools python-dev libffi-dev
  sudo /usr/bin/pip install cffi
  git clone https://github.com/maxlklaxl/python-tsl2591.git
"""

import tsl2591


class LuxSensor:
    tsl = None
    def __init__(self, sensor_id=1):
        self.sensor_id = sensor_id
        if LuxSensor.tsl is None:
            LuxSensor.tsl = tsl2591.Tsl2591() # initialize the sensor context

    def sample(self):
        """Read the tsl2591 lux sensor and dispatch the luminosity value.
        """
        full, ir = LuxSensor.tsl.get_full_luminosity()
        lux = LuxSensor.tsl.calculate_lux(full, ir)
        # we convert the lux value to an integer - fractions are not
        # significant.
        return int(round(lux, 0))

    def __str__(self):
        return 'LuxSensor(%s)' % self.sensor_id
