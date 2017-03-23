# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
Output on raspberry pi gpio pins
"""

import RPi.GPIO as gpio

from thingflow.base import InputThing, SensorEvent

class GpioPinOut(InputThing):
    """Actuator for an output pin on the GPIO bus.
    """
    def __init__(self, port=11):
        self.port = port
        gpio.setmode(gpio.BOARD)
        gpio.setup(port, gpio.OUT, initial=gpio.LOW)
        self.current_state = False
        self.closed = False

    def on_next(self, x):
        """If x is a truthy value, we turn the light on
        """
        assert not isinstance(x, SensorEvent), "Send a raw value, not a sensor event"
        if x and not self.current_state:
            gpio.output(self.port, gpio.HIGH)
            self.current_state = True
        elif (not x) and self.current_state:
            gpio.output(self.port, gpio.LOW)
            self.current_state = False

    def _cleanup(self):
        if not self.closed:
            gpio.output(self.port, gpio.LOW)
            gpio.cleanup()
        self.closed = True
        
    def on_completed(self):
        self._cleanup()

    def on_error(self, e):
        self._cleanup()

    def __str__(self):
        return "GpioPinOut(port=%s, state=%s)" % \
            (self.port, 'ON' if self.current_state else 'OFF')

