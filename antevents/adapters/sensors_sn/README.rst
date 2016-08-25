===========================
Ant Events Sensor Adapters
===========================

These files allow some sensors to be used with the Raspberry Pi and Arduino 
microcontrollers.

adxl345_py3.py
--------------
Python library from https://github.com/pimoroni/adxl345-python with a minor edit
to allow it to be used in Python 3 (print statement)

adxl345_upy.py
--------------
As above, with further edits to allow it to be used in MicroPython, which does not
have the smbus module

sensor.py
---------
Contains two classes of sensors.

RPISensor(): 	  Allows digital (1/0 output) sensors to be connected straight to the
		  Raspberry Pi (ADC needed for the Pi to take analogue output
ArduinoSensors(): Allows digital (1/0 output) and analogue (0-1023 ouput) sensors to
		  be connected to the Arduino. To use this, Nanpy firmware needs to be
		  flashed onto the Arduino to allow Python to be used.

main_adxl345_upython.py
-----------------------
Script used on the ESP8266 to collect sensor data and send it to an MQTT broker.
To use it, the parameters in the file need to be set (WIFI_SID, WIFI_PW, BROKER) and
the file renamed to 'main.py' which will be run when the ESP8266 is booted. Mpfshell
is recommended for transferring MicroPython files to the ESP8266.

Usage
=====
The classes have been edited to match the API changes Jeff proposed, so they can be
used as follows:
  sensor = SensorPub(RPISensor())

Note
====
The classes in sensor.py can only be used with sensors which send their output straight
to the Raspberry Pi and Arduino pins. For sensors which use I2C or SPI, with their
own registers, a library to use them has to be written separately.