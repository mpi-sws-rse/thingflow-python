=================================
Raspberry Pi Light Sensor Example
=================================

This directory contains two example AntEvents applications that read a tsl2591
Lux sensor connected to a Raspberry Pi running Raspbian Linux. To run these
examples, you need to install several packages, as follows::

    sudo apt-get install build-essential libi2c-dev i2c-tools python-dev libffi-dev
    sudo /usr/bin/pip install cffi
    git clone https://github.com/maxlklaxl/python-tsl2591.git
    cd python-tsl2591; python setup.py install

Single Process Example
----------------------
The script ``lux_sensor_example.py`` is a single process application that
samples from the lux sensor, prints the events obtained, and activates an LED
on the Pi's GPIO bus if a threshold lux value is exceeded.

Distributed Example
--------------------
``dist_lux_rpi.py`` and ``dist_lux_server.py`` implement a distributed Lux data
collector. The ``dist_lux_rpi.py`` script runs on the Pi and has the same
functionality as the single process example. Additionally, it sends the sensor
events to a MQTT broker. The ``dist_lux_server.py`` script runs on a server that
has the PostgreSQL database installed. The server-side script reads events from
the MQTT queue and saves them to the database.
