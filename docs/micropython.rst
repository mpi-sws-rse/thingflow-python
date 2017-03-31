
6. ThingFlow-MicroPython Port
=============================
This section describes the  port of ThingFlow to MicroPython_, a bare-metal implementation of
Python 3 for small processors. This port has been tested on the ESP8266_
using version 1.8.7 of MicroPython.

MicroPython has only a subset of the libraries that come with the standard
CPython implementation. For example, an event library, threading, and even
logging are missing. This ThingFlow port currently only provides a subset of the
ThingFlow functionality, due to the library limitation and memory limitations
on the ESP8266.. The assumption is that processors like
the ESP8266 are used primarily to sample sensor data and pass it on to
a larger system (e.g. a Raspberry Pi or a server).

The code for this port may
be found in the main ThingFlow-Python repository, under the ``micropython``
subdirectory.
The core implementation is in ``miropython/thingflow.py``.
The other files (``logger.py``,
``mqtt_writer.py``, and ``wifi.py``) provide some additional utilities.

.. _MicroPython: http://www.micropython.org
.. _ESP8266: https://en.wikipedia.org/wiki/ESP8266

Installing
-----------
Just copy the python files in this directory to your MicroPython board.
MicroPython's webrepl has experimental support for copying files. I
instead used mpfshell_ to copy files to my ESP8266 board.

To free up more memory, I disabled the starting if the webrepl in the
``boot.py`` script.

.. _mpfshell: https://github.com/wedlers/mpfshell

Bug Workarounds
---------------
The thingflow code has a few workarounds for bugs in MicroPython (at least
the ESP8266 port).

Clock wrapping
~~~~~~~~~~~~~~
The clock on the ESP8266 wraps once every few hours. This causes problems when
we wish to measure sleep time. The ``utime.ticks_diff()`` function is
supposed to handle this, bug apparently is buggy. This leads to cases where
the calculation:::

    int(round(utime.ticks_diff(end_ts, now)/1000))

yields 1,069,506 seconds instead of 59 seconds. Luckily, an assert in
``_advance_time`` caught the issue. The clock had clearly wrapped as
``end_ts`` (the earlier time) was 4266929 and the current timestamp was 30963.

Long variable names for keyword arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
There is a bug in MicroPython where keyword argument names longer than 10
characters can result in a incorrect exception saying that keyword arguments
are not implemented. I think this is related to MicroPython issue #1998.

Sensors
-------
Sensor code for the MicroPython port are in the ``sensors`` subdirectory.
See the ``README.rst`` file in that directory for details.

Design Notes
------------

Scheduler Design
~~~~~~~~~~~~~~~~
Since MicroPython does not provide an event scheduler, [#]_ we provide one directly
in ``thingflow.py``. This scheduler is optimized for minimal power consumption (by
reducing wake-ups) rather than for robustness in the face of tight deadlines.

The scheduler has two layers: the *internal* layer (represented by the methods
starting with an underscore) and the *public* layer. The public layer provides
an API similar to the standard ThingFlow scheduler and is built on the internal
layer.

For ease of testing and flexibility, the internal layer is designed such that the
sensor sampling and the sleeps between events happen outside it. The internal
layer is responsible for determining sleep times and the set of tasks to
sample at each wakeup.

Time within the internal layer is measured in "ticks". Currently, one tick
is 10 ms (1 "centisecond").  Fractional ticks are
not allowed, to account for systems that cannot handle floating point sleep
times. The scheduler tracks the current logical time in ticks and updates
this based on elapsed time. To avoid issues with unexpected wrapping of the
logical clock, it is automatically wrapped every 65535 ticks. The logical
times for each for each scheduled task are then updated to reflect the wrapped
clock.

When a task (output_thing) is added to the scheduler, a sample interval is
specified. To optimize for wakeups, the following approaches are used:

1. Tasks with the same interval are always scheduled together. If a new task is
   added that matches an older task's interval, it will not be scheduled until
   the existing one is run.
2. If there are no tasks with the same interval, we look for the smallest
   interval that is either a factor or multiple of the new interval. We
   schedule the new interval to be coordinated with this one. For example, if
   we have a new interval 60 seconds and old intervals 30/45 seconds, we will
   schedule the new 60 second interval to first run on the next execution
   of the 30 second tasks. Thus, they will run at the same time for each
   execution of the 60 second interval.
3. The next time for a task is maintained in logical ticks. If a task is run
   later than its interval, the next scheduled execution is kept as if the task
   had run at the correct time (by making the interval shorter). This avoids
   tasks getting out-of-sync when one misses a deadline.

The public API layer is a subset of the standard ThingFlow scheduler API,
except for the additional ``schedule_sensor`` convenience method.

.. [#] I have heard rumors about a port of the ``async`` library to MicroPython.
       However, it still makes sense to use this custom scheduler, as it is
       likely to be more power efficent due to its strategy of scheduling
       events together.

Logger
~~~~~~
 ``logger.py`` provides a very simple rotating file logger with an API that
 is a subset of Python's ``logging`` API. Given a log file ``outputfile``,
 it will log events to that file until the length would exceed ``max_len``.
 At that point, it renames the file to ``outputfile``.1 and then starts
 a new logfile. Thus, the maximum size of the logs at any given time should
 be 2*``max_len``.

 To use the logger, you need to first call ``initialize_logging()``. You can
 then call ``get_logger()`` to get the logger instance. Note that there is a
 single global log level. The whole mess of handlers, formatters, and filters
 is not provided.
