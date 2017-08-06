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

mcp9808.py
----------
A sensor for the MCP9808 temperature sensor breakout board from Adafuit. This
is a port to MicroPython of
`Adafruit-MCP9808 <https://github.com/adafruit/Adafruit_Python_MCP9808/>`__.

adxl345_upy.py
--------------
Sensor for ADXL345 digital accelerometer. The python library is originally from
https://github.com/pimoroni/adxl345-python with edits for Micropython (that does
not have the smbus module) and Python 3 (print statement).

adc_esp8266.py
--------------
Analog to digital sensor for the esp8266 microcontroller. Original
implementation from https://github.com/mzdaniel/micropython-iot
The file is included here for convenience.
