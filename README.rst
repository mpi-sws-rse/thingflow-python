===========
ThingFlow
===========

ThingFlow is a (Python3) framework for building IoT event
processing dataflows. [#]_  The goal of this framework is to support the
creation of robust IoT systems from reusable components. These systems must
account for noisy/missing sensor data, distributed computation, and the need for
local (near the data source) processing.

The source repository for ThingFlow-python is at https://github.com/mpi-sws-rse/thingflow-python.

Introduction
============
The fundamental abstractions in ThingFlow are:

1. *sensors*, which provide a means
   to sample a changing value representing some quanity in the physical world,
2. *event streams*, which are push-based sequences of sensor data readings, and
3. *things*, which are reusable components to generate, transform, or consume the events on these streams.

Things can have simple, stateless logic (e.g. filter events based
on a predicate) or implement more complex, stateful algorithms, such as
Kalman filters or machine learning. Using ThingFlow, you describe the flow of
data through these things rather than programming low-level behaviors. 

Although ThingFlow presents a simple dataflow model to the user, internally it
uses an event-driven programming model, building on
Python's ``asyncio`` module. In addition to being a natural programming model for
realtime sensor data, it reduces the potential resource consumption of Ant
Events programs. The details of event scheduling are handled by the framework.
Separate threads may be used on the "edges" of a dataflow, where elements
frequently interact with external components that have blocking APIs.

ThingFlow integrates with standard Python
data analytics frameworks, including NumPy_, Pandas_, and scikit-learn_. This
allows dataflows involving complex elements to be developed and refined offline
and then deployed in an IoT environment using the same code base.

We call the implementation described here "ThingFlow-Python", as it should be
possible to port the ideas of ThingFlow to other languages. Currently, one such
port exists: "ThingFlow-MicroPython". This is a port ThingFlow to MicroPython,
a limited version of Python 3 that runs "bare metal" on embadded devices. The
ThingFlow-MicroPython port is included in the ThingFlow-Python repository
under the subdirector ``micropython``. It is documented in
`a chapter <http://thingflow-python.readthedocs.io/en/latest/micropython.html>`_
of the documentation.


.. _NumPy: http://www.numpy.org/
.. _Pandas: http://pandas.pydata.org/
.. _scikit-learn: http://scikit-learn.org/stable/

Example
-------
To give the flavor of ThingFlow, below is a short code snippet for the
Raspberry Pi that reads a light sensor and then turns on an LED if the running
average of the last five readings is greater than some threshold::

    lux = SensorAsOutputThing(LuxSensor())
    lux.map(lambda e: e.val).running_avg(5).map(lambda v: v > THRESHOLD)\
       .GpioPinOut()
    scheduler.schedule_periodic(lux, 60.0)
    scheduler.run_forever()

The first line instantiates a light sensor object and wraps it in an *output thing*
to handle sampling and progagation of events.

The next two lines
create a pipeline of things to process the data from the sensor. We call things
which have a single input and output *filters*, as they can be composed to process
a stream of events.
The ``map`` filter extracts the data value from the sensor event, the
``running_avg`` filter averages the last five values, and the next ``map`` filter converts
the value to a a boolean based on the threshold.  The ``GpioPinOut`` thing is
an *adapter* to the outside world. It turns on the LED based on the value of
its input boolean value.

Finally, the last two lines of the example schedule the sensor to be sampled
at a sixty second interval and then start the scheduler's main loop.

Dependencies
------------
The ThingFlow proper is self-contained. You do not need any dependencies other
than Python 3 (3.4 or later). Specific adapters and sensors may have additional
dependencies (e.g. the MQTT adapters depend on MQTT client libraries).

Documentation
-------------
Documentation is hosted online at http://thingflow-python.readthedocs.io.

The source tree for the documentation is in the ``docs`` subdirectory - it is
built using `Sphinx <http://www.sphinx-doc.org/en/stable/>`_. If you have Sphinx
installed locally (along with the "Read the Docs" theme), you can also build it
directly on your machine.


.. [#] *ThingFlow* was originally known as *AntEvents*.

