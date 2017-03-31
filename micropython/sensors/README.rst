=======================================
Sensors for ThingFlow, Micropython Port
========================================

These are typically copied directly to the root directory on the micropython
system.  Due to memory limitations, the comments are pretty sparse.

Some sensors are adaptations of third party code. Those cases are noted below.
Those files are made available under their original open source licenses.

tsl2591.py
----------
A sensor for the TSL2591 light sensor breakout board from Adafruit. This is a
port to Micropython of `python-tsl2591 <https://github.com/maxlklaxl/python-tsl2591>`_.
The port has its own github repo at https://github.com/jfischer/micropython-tsl2591.
The file is included here for convenience.

adxl345_upy.py
--------------
Sensor for ADXL345 digital accelerometer. The python library is originally from
https://github.com/pimoroni/adxl345-python with edits for Micropython (that does
not have the smbus module) and Python 3 (print statement).

