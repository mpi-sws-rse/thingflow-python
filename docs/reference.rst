.. _reference:

9. ThingFlow-Python API Reference
=================================

.. automodule:: thingflow
   :members:

thingflow.base
--------------

.. automodule:: thingflow.base
   :members:


thingflow.sensors
-----------------
The sensors are not included in the auto-generated
documentation, as importing the code requires external
libraries (not possible for automated documentation generation).
Here is a list of available sensor modules in the ThingFlow-Python
distribution:

* ``rpi.adxl345_py3`` - interface to the adxl345 accelerometer
* ``rpi.arduino`` - interface an Arduino to the Raspberry Pi
* ``rpi.gpio`` - read from the Raspberry Pi GPIO pins
* ``lux_sensor`` - read from a TSL2591 lux sensor
  
Please see the source code for more details on these sensors.

thingflow.filters
-----------------

.. automodule:: thingflow.filters
   :members:

thingflow.filters.buffer
~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.buffer
   :members:

thingflow.filters.combinators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.combinators
   :members:

thingflow.filters.dispatch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.dispatch
   :members:

thingflow.filters.first
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.first
   :members:

thingflow.filters.json
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.json
   :members:

thingflow.filters.map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.map
   :members:

thingflow.filters.never
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.never
   :members:

thingflow.filters.output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.output
   :members:

thingflow.filters.scan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.scan
   :members:
      
thingflow.filters.select
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.select
   :members:

thingflow.filters.skip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.skip
   :members:
      
thingflow.filters.some
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.some
   :members:
      
thingflow.filters.take
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.take
   :members:
      
thingflow.filters.timeout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.timeout
   :members:
      
thingflow.filters.transducer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.transducer
   :members:
      
thingflow.filters.where
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.filters.where
   :members:


thingflow.adapters
------------------
.. automodule:: thingflow.adapters
   :members:

thingflow.adapters.csv
~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.adapters.csv
   :members:

thingflow.adapters.generic
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: thingflow.adapters.generic
   :members:

Other Adapters
~~~~~~~~~~~~~~
Many adapters are not included in the auto-generated documentation, as
importing the code requires external libraries (not possible for the
auto document generation). Here is a list of additional adapters
in the ThingFlow-Python distirbution:

* ``bokeh`` - interface to the Bokeh visualization framework
* ``influxdb`` - interface to the InfluxDb time series database
* ``mqtt`` - interface to MQTT via ``paho.mqtt``
* ``mqtt_async`` - interface to MQTT via ``hbmqtt``
* ``pandas`` - convert ThingFlow events to Pandas ``Series`` data arrays
* ``predix`` - send and query data with the GE Predix Time Series API
* ``postgres`` - interface to the PostgreSQL database
* ``rpi.gpio`` - output on the Raspberry Pi GPIO pins



Please see the source code for more details
on these adapters. 
