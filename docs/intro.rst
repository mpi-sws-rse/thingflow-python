.. _intro:

1. Introduction
===============
The fundamental abstractions in ThingFlow are 1) *sensors*, which provide a means
to sample a changing value representing some quanity in the physical world, 2)
*event streams*, which are
push-based sequences of sensor data readings, and 3) *things*, which are
reusable components to generate, transform, or consume the events on these
streams. Things can have simple, stateless logic (e.g. filter events based
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
port exists: "ThingFlow-MicroPython". This is a port of ThingFlow to MicroPython,
a limited version of Python 3 that runs "bare metal" on embadded devices. The
ThingFlow-MicroPython port is included in the ThingFlow-Python repository
under the subdirectory ``micropython``. It is documented in
:ref:`Section 7 <micropython_port>` of this document.


.. _NumPy: http://www.numpy.org/
.. _Pandas: http://pandas.pydata.org/
.. _scikit-learn: http://scikit-learn.org/stable/

Example
-------
To give the flavor of ThingFlow, below is a short code snippet for the
Raspberry Pi that reads a light sensor and then turns on an LED if the running
average of the last five readings is greater than some threshold:

.. code-block:: python

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

Platforms
---------
ThingFlow does not have any required external dependendencies, so, in theory
at least, it can be run just about anywhere you can run Python 3. It has been
tested on the Raspberry Pi (Rasbian distribution), Desktop Linux, and MacOSX.
In a desktop environment, you might find the
Anaconda_ Python distribution helpful, as it comes with many data analytics
tools (e.g. Jupyter, NumPy, Pandas, and scikit-learn) pre-installed.

ThingFlow has been ported to Micropython_, so that it can run on very small
devices, like the ESP8266_. Since these devices have stringent memory
requirements, the code base has been stripped down to a core for the
Micropython port. The port is in this repository under the ``micropython``
directory.

.. _Micropython: http://www.micropython.org
.. _ESP8266: http://docs.micropython.org/en/latest/esp8266/esp8266/quickref.html
.. _Anaconda: https://docs.continuum.io/anaconda/index

Installing ThingFlow
---------------------
We recommend installing into a ``virtualenv`` rather than directly into the
system's Python. To do so, first run the ``activate`` script of your chosen
virtual environment. Next, you can either install from the Python Package
Index website (pypi.python.org) or from the ThingFlow source
tree.

Installing from the Python Package Index
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The package name of thingflow-python on PyPi is ``thingflow``. You
can use the ``pip`` utility to install, as follows::

      pip3 install thingflow

If you have activated your virtual environment, this should pick up the
version of ``pip3`` associated with your environment, and install ThingFlow
into your environment rather than into the system's Python install.

Installing from the source tree
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Go to the ``thingflow-python`` directory and then run::

    python3 setup.py install

If you have activated your virtual environment, this should pick up the
version of ``python3`` associated with your environment, and install ThingFlow
into your environment rather than into the system's Python install.
    
    

Using ThingFlow without installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can also run the ThingFlow code in-place from the git repository by adding
the full path to the ``thingflow-python`` directory to your ``PYTHONPATH``. This
is how the tests and the examples are run.

Directory Layout
----------------
The layout of the files in the ThingFlow code repository (the ``thingflow-python``
directory) is as follows:

+ ``README.RST`` - a short introduction and pointer to resources
+ ``Makefile`` - builds the source distribution and documentation; can run the tests
+ ``setup.py`` - used to install the core code into a python environment
+ ``thingflow/`` - the core code. This is all that will get installed in a
  production system

  + ``thingflow/base.py`` - the core definitions and base classes of thingflow
  + ``thingflow/adapters`` - reader and writer things that talk to the outside world
  + ``thingflow/filters`` - elements for filter pipelines, in the style of
    Microsoft's Linq_ framework

+ ``docs/`` - this documentation, build using Sphinx
+ ``tests/`` - the tests. These can be run in-place.
+ ``examples/`` - examples and other documentation.
+ ``micropython/`` - port of the ThingFlow core to MicroPython


.. _Linq: https://en.wikipedia.org/wiki/Language_Integrated_Query


More Examples
-------------
There is also a separate repository with larger ThingFlow examples. It is at
https://github.com/mpi-sws-rse/thingflow-examples. This repository includes an automated
lighting application and a vehicle traffic analysis.

Next, we will go into more detail on ThingFlow with a :ref:`tutorial <tutorial>`.
