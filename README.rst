===========
Ant Events
===========

Introduction
============
Ant Events is a (Python3) framework for building IOT event
processing dataflows. The goal of this framework is to support the
creation of robust IoT systems from reusable components. These systems must
account for noisy/missing sensor data, distributed computation, and the need for
local (near the data source) processing.

The fundamental abstractions in Ant Events are *event streams*, which are
push-based sequences of sensor data readings, and *elements*, which are
reusable components to generate, transform, or consume the events on these
streams. Elements can have simple, stateless logic (e.g. filter events based
on a predicate) or implement more complex, stateful algorithms, such as
Kalman filters or machine learning. Ant Events integrates with standard Python
data analytics frameworks, including NumPy_, Pandas_, and scikit-learn_. This
allows dataflows involving complex elements to be developed and refined offline
and then deployed in an IoT environment using the same code base.

Ant Events primarily uses an event-driven programming model, building on
Python's ``asyncio`` module. In addition to being a natural programming model for
realtime sensor data, it reduces the potential resource consumption of Ant
Events programs. The details of event scheduling are handled by the framework.
Separate threads may be used on the "edges" of a dataflow, where elements
frequently interact with external components that have blocking APIs.

.. _NumPy: http://www.numpy.org/
.. _Pandas: http://pandas.pydata.org/
.. _scikit-learn: http://scikit-learn.org/stable/

Example
-------
To give the flavor of Ant Events, below is a short code snippet for the
Raspberry Pi that reads a light sensor and then turns on an LED if the running
average of the last five readings is greater than some threshold::

    lux = LuxSensor()
    lux.select(lambda e: e.val).running_avg(5)\
       .select(lambda v: v > THRESHOLD).GpioPinOut()

The first line creates an element representing sensor object and the second line
creates a pipeline of elements to process the data from the element. The
``select`` element extracts the data value from the sensor event, the
``running_avg`` element averages the values, the next ``select`` element converts
the value to a a boolean based on the threshold, and the ``GpioPinOut`` element
turns on the LED based on the value of the boolean.

Getting Started
===============
Platforms
---------
Ant Events does not have any required external dependendencies, so, in theory
at least, it can be run just about anywhere you can run Python 3. It has been
tested on the Raspberry Pi (Rasbian distribution), Desktop Linux, and MacOSX.
In a desktop environment, you might find the
Anaconda_ Python distribution helpful, as it comes with many data analytics
tools (e.g. Jupyter, NumPy, Pandas, and scikit-learn) pre-installed.

Ant Events has been ported to Micropython_, so that it can run on very small
devices, like the ESP8266_. Since these devices have stringent memory
requirements, the code base has been stripped down to a core for the
Micropython port. The port is in this repository under the ``micropython``
directory.

.. _Micropython: http://www.micropython.org
.. _ESP8266: http://docs.micropython.org/en/latest/esp8266/esp8266/quickref.html
.. _Anaconda: https://docs.continuum.io/anaconda/index

Installing Ant Events
---------------------
We recommend installing into a ``virtualenv`` rather than directly into the
system's Python. To install, first run the ``activate`` script of your chosen
virtual environment, and go to the ``antevents-python`` directory. Then run::

    python3 setup.py install

In the future, we will have support for installing from the Python Package
Index, PyPi.

You can also run the Ant Events code in-place from the git repository by adding
the full path to the ``antevents-python`` directory to your ``PYTHONPATH``. This
is how the tests and the examples are run.

Directory Layout
----------------
The layout of the files in the Ant Events code repository (the ``antevents-python``
directory) is as follows:

+ ``README.RST`` - this file, top level documentation
+ ``Makefile`` - builds the source distribution and documentation; can run the tests
+ ``setup.py`` - used to install the core code into a python environment
+ ``antevents/`` - the core code. This is all that will get installed in a
  production system

  + ``antevents/base.py`` - the core definitions and base classes of antevents
  + ``antevents/adapters`` - reader and writer elements that talk to the outside world
  + ``antevents/linq`` - elements for filter pipelines, in the style of
    Microsoft's Linq_ framework

+ ``docs/`` - documentation, in restructured text (.rst) format.
+ ``tests/`` - the tests. These can be run in-place.
+ ``examples/`` - examples and other documentation.

  + ``examples/notebooks`` - examples that use Jupyter

+ ``micropython/`` - port of Ant Events core to Micropython


.. _Linq: https://en.wikipedia.org/wiki/Language_Integrated_Query


Next Steps
==========
To learn more about AntEvents, look at the ``docs/`` subdirectory. In
particular, ``tutorial.rst`` is a good starting point.

There is a separate repository with larger AntEvents examples. It is at
https://github.com/mpi-sws-rse/antevents-examples.

Related Work
============
The architecture was heavily influenced by Microsoft's Rx_ (Reactive Extensions)
framework and the Click_ modular router. We started by trying to simplfy Rx for
the IoT case and remove some of the .NETisms. A key addition was the support for
multiple topics, which makes more complex dataflows possible.

.. _Rx: https://msdn.microsoft.com/en-us/data/gg577609.aspx
.. _Click: http://read.cs.ucla.edu/click/click



