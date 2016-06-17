"""
To install the tsl2591 library:
  sudo apt-get install build-essential libi2c-dev i2c-tools python-dev libffi-dev
  sudo /usr/bin/pip install cffi
  git clone https://github.com/maxlklaxl/python-tsl2591.git
"""

import time
import tsl2591


from antevents.base import Publisher, IndirectPublisherMixin
from antevents.sensor import SensorEvent





class LuxSensor(Publisher, IndirectPublisherMixin):
    tsl = None
    def __init__(self, sensor_id=1):
        super().__init__()
        self.sensor_id = sensor_id
        if LuxSensor.tsl is None:
            LuxSensor.tsl = tsl2591.Tsl2591() # initialize the sensor context

    def _observe_and_enqueue(self):
        """Read the tsl2591 lux sensor and dispatch the luminosity value.
        """
        try:
            full, ir = LuxSensor.tsl.get_full_luminosity()
            lux = LuxSensor.tsl.calculate_lux(full, ir)
        except Exception as e:
            self._dispatch_error(e)
        else:
            # we convert the lux value to an integer - fractions are not
            # significant.
            lux_as_int = int(round(lux, 0))
            self._dispatch_next(SensorEvent(sensor_id=self.sensor_id, ts=time.time(),
                                            val=lux_as_int))
            return True

    def __str__(self):
        return 'LuxSensor(1)'
