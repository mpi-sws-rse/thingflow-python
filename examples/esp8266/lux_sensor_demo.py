# Simple demo of reading the tsl2591 lux sensor from the
# ESP8266 running micropython.

from thingflow import *
from tsl2591 import Tsl2591
tsl = Tsl2591('lux-1')
tsl.sample()
sched = Scheduler()

class Output:
    def on_next(self, x):
        print(x)
    def on_completed():
        pass
    def on_error(self, e):
        pass

sched.schedule_sensor(tsl, 2.0, Output())
sched.run_forever()
