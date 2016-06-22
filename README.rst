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
Python's `asyncio` module. In addition to being a natural programming model for
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
`select` element extracts the data value from the sensor event, the
`running_avg` element averages the values, the next `select` element converts
the value to a a boolean based on the threshold, and the `GpioPinOut` element
turns on the LED based on the value of the boolean.

Getting Started
===============
Platforms
---------
Ant Events does not have any required external dependendencies, so, in theory
at least, it can be run just about anywhere you can run Python 3. It has been
tested on the Raspberry Pi (Rasbian distribution), Desktop Linux, and MacOSX.
Work is underway to port it to Micropython_, so that it can run on very small
devices, like the ESP8266_. In a desktop environment, you might find the
Anaconda_ Python distribution helpful, as it comes with many data analytics
tools (e.g. Jupyter, NumPy, Pandas, and scikit-learn) pre-installed.

.. _Micropython: http://www.micropython.org
.. _ESP8266: http://docs.micropython.org/en/latest/esp8266/esp8266/quickref.html
.. _Anaconda: https://docs.continuum.io/anaconda/index

Installing Ant Events
---------------------
We recommend installing into a `virtualenv` rather than directly into the
system's Python. To install, first run the `activate` script of your chosen
virtual environment, and go to the `antevents-python` directory. Then run::

    python3 setup.py install

In the future, we will have support for installing from the Python Package
Index, PyPi.

You can also run the Ant Events code in-place from the git repository by adding
the full path to the `antevents-python` directory to your `PYTHONPATH`. This
is how the tests and the examples are run.

Directory Layout
----------------
The layout of the files in the Ant Events code repository (the `antevents-python`
directory) is as follows:

+ `README.RST` - this file, top level documentation
+ `Makefile` - builds the source distribution and documentation; can run the tests
+ `setup.py` - used to install the core code into a python environment
+ `antevents/` - the core code. This is all that will get installed in a
  production system

  + `antevents/base.py` - the core definitions and base classes of antevents
  + `antevents/adapters` - reader and writer elements that talk to the outside world
  + `antevents/linq` - elements for filter pipelines, in the style of
    Microsoft's Linq_ framework
      
+ `tests/` - the tests. These can be run in-place.
+ `examples/` - examples and other documentation.

  + `examples/notebooks` - examples that use Jupyter


.. _Linq: https://en.wikipedia.org/wiki/Language_Integrated_Query


Tutorial
=========
To understand the core concepts in Ant Events, let us build a simple app with a
dummy sensor that generates random data and feeds it to a dummy LED. The final
code for this example is at `examples/tutorial.py`.

Publishers and Subscribers
--------------------------
First a little background on the core abstractions in Ant Events.
Each Ant Events element is either a *publisher*, which
sources events and and puts the into the workflow, a *subscriber*, which sinks
events, accepting event streams from the workflow, or both. Elements that are
only publishers are called *readers* and include sensors and other components
that read events from outside data sources. Elements that are only subscribers
are called *writers* and include actuators and other components that write
events to outside data sensors. Elements that are both a publisher and a
subscriber are called *filters* and are used to transform event streams.

A publisher may create multiple output event streams. These are called
*topics*. Likewise, a subscriber may accept multiple input event streams by
subscribing to multiple topics. When a subscriber subscribes to a topic, it
can specify a mapping between the publisher's name for the topic and the
subscriber's name. This makes it easier to combine components in unanticipated
ways. In general, we can connect a subscriber to a publisher through the
publisher's `subscribe()` method like this::

    publisher.subscribe(subscriber,
                        topic_mapping=('pub_topic_name', 'sub_topic_name'))

There also exists a special *default* topic, which is used when no topic
is specified on a subscription. If you leave off the topic mapping
parameter in the subscribe call, it maps the default topic of the
publisher to the default topic of the subscriber::

    publisher.subscribe(subscriber)

Once connected through the subscribe call, a publisher and subscriber interact
through three methods on the subscriber:

* `on_next`, which passes the next event in the stream to the subscriber.
* `on_error`, which should be called at most once, if a fatal error occurs. The
  exception that caused the error is passed as the parameter.
* `on_completed`, which signals the end of the stream and takes no parameters.

Implementing a Publisher
~~~~~~~~~~~~~~~~~~~~~~~~
When implmenting a publisher, one subsclasses from `antevents.base.Publisher`.
To emit a new event, the subclass calls the `_dispatch_next` method with the
event and topic name. To signal an error or completion of the event stream,
once calls `_dispatch_error` or `_dispatch_completed`, respectively. The base
class implementation of these methods is responsible for calling the `on_next`,
`on_error`, and `on_completed` methods for each of the subscribers.

The code to call these `_dispatch` methods goes in a well-known method to be
called by the scheduler. The specific method depends on whether the code to
capture events must be run in a separate thread (blocking). There are three
cases supported by Ant Events and three associated mixin-classes that define
the methods:

1. `DirectPublisherMixin` defines an `_observe` method that can be called
   directly by the scheduler in the main thread.
2. `IndirectPublisherMixin` defines an `_observe_and_equeue` method that can
   will be called from a dedicated thread. The subscribers are then called
   in the main thread.
3. `EventLoopPublisherMixin` is used for a publisher that has its own separate
   event loop. This is run in a separate thread and the subscribers called
   in the main thread.

OK, with all that out of the way, let us define a simple sensor. Sensors are
publishers and thus inherit from the `Publisher` class. We also inherit from
`DirectPublisherMixin` and implement the `_observe` method, as we will call
this sensor directly from the main thread. Here is the code::

    import random
    random.seed()
    import time
    from antevents.base import Publisher, DirectPublisherMixin
    from antevents.sensor import SensorEvent
    
    class RandomSensor(Publisher, DirectPublisherMixin):
        """Generate a random value each time the sensor is called.
	"""
        def __init__(self, sensor_id, mean, stddev):
            super().__init__()
            self.sensor_id = sensor_id
            self.mean = mean
            self.stddev = stddev
    
        def _observe(self):
            """Sample the sensor and dispatch to the subscribers.
            """
            evt = SensorEvent(self.sensor_id, time.time(),
                              random.gauss(self.mean, self.stddev))
            self._dispatch_next(evt)
            return True # more data potentially available
    
        def __str__(self):
            return "RandomSensor(%s, %s, %s)" % \
                (self.sensor_id, self.mean, self.stddev)


The main action for this code is happening in `_observe`: we create a
`SensorEvent` instance and then dispatch it to the publisher machinery. We
return `True` to indicate to the scheduler that there could potentially be
more events (we did not call the `_dispatch_completed` or `_dispatch_error`
methods). `SensorEvent`, which is defined in `antevents.sensor`, is a named
tuple that provides a simple representation of events, with a sensor id, a
timestamp, and a value. The Ant Events infrastructure is not hard-coded to
use this definition for an event, but it is made available for convenience.

Now, we can instantiate our sensor::

    MEAN = 100
    STDDEV = 10
    sensor = RandomSensor(1, MEAN, STDDEV)

Implementing an Subscriber
~~~~~~~~~~~~~~~~~~~~~~~~~~
Now, let us define a simple subscriber -- a dummy LED actuator. The LED will
inherit from the `antevents.base.DefaultSubscriber` class, which defines the
subscriber interface. Here is the code::

    from antevents.base import DefaultSubscriber
    class LED(DefaultSubscriber):
        def on_next(self, x):
            if x:
                print("On")
            else:
                print("Off")
    
        def on_error(self, e):
            print("Got an error: %s" % e)
    
        def on_completed(self):
            print("LED Completed")
    
        def __str__(self):
            return 'LED'

As you can see, the main logic is in `on_next` -- if the event looks like a true
value, we just print "On", otherwise we print "Off". We won't do anything
special for the `on_error` and `on_completed` callbacks. Now, we can instantiate
an LED::

    led = LED()

Filters
-------
A *filter* is a component that accepts a single
input event stream on the default topic and outputs a single event stream on the
default topics. Through Python package imports and some Python metaprogramming,
you can dynamically add various convenience methods to the `Publisher` base
class that create and return filters. This allows filters can be easily chained
together, implementing multi-step query pipelines without any glue code.

Let us now create a series of filters that connect together our dummy light
sensor and our LED. Here is some code to look at each event and send `True` to
the LED if the value exceeds the mean (provided to the sensor) and `False`
otherwise::

    import antevents.linq.select
    sensor.select(lambda evt: evt.val > MEAN).subscribe(led)

The `import` statement loads the code for the `select` filter. By loading it,
it is added as a method to the `Publisher` class. Since the sensor is a
`RandomSensor`, which inherits from `Publisher`, it gets this method as well.
Calling the method creates a filter element which runs the supplied anonymous
function on each event and passes the result to its subscribers. This filter is
automatically subscribed to the `sensor` element's default event stream. The
`select` call returns the filter element, allowing it to be used in chained
method calls. In this case, we `subscribe` the `led` to the filter's event
stream.

Example
~~~~~~~
Imagine that the sensor outputs the following three events, separated by 10
seconds each::

    SensorEvent(1, 2016-06-21T17:43:25, 95)
    SensorEvent(1, 2016-06-21T17:43:35, 101)
    SensorEvent(1, 2016-06-21T17:43:45, 98)

The `select` filter would output the following::

    False
    True
    False

The LED would print the following::

    Off
    On
    Off

Some Debug Output
~~~~~~~~~~~~~~~~~
There are a number of approaches one can take to help understand the behavior of
an event dataflow.  First, can add an `output` element to various points in the
flow. The `output` element just prints each event that it see. It is another
linq-style filter that can be added to the base publisher class by importing the
associated Python package. For example, here is how we add it as a subscriber to
our sensor, to print out every event the sensor emits::

    import antevents.linq.output
    sensor.output()

Note that this does not actually print anything yet, we have to run the
*scheduler* to start up our dataflow and begin sampling events from the sensor.

Another useful debugging tool is the `print_downstream` method on the
`Publisher`. It can be called on any publisher subclass to see a representation
of the event tree rooted at the given publisher. For example, here is what we
get when we call it on the `sensor` at this point::

    ***** Dump of all paths from RandomSensor(1, 100, 10) *****
      RandomSensor(1, 100, 10) => select => LED
      RandomSensor(1, 100, 10) => output
    ************************************

The Scheduler
-------------
As you can see, it is easy to create these pipelines. However, this sequence of
publishers and subscribers will do nothing until we hook it into the main
event loop. In particular, any publishers that source events into the system
(e.g. sensors) must be made known to the *scheduler*. Here is an example where
we take the dataflow rooted at the light sensor, tell the scheduler to sample it
once every second, and then start up the event loop::

    import asyncio
    from antevents.base import Scheduler
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_periodic(sensor, 1.0) # sample once a second
    scheduler.run_forever() # will run until there are no more active sensors
    print("That's all folks!") # This will never get called in the current version
  
The output will look something like this::

    Off
    SensorEvent(sensor_id=1, ts=1466554963.321487, val=91.80221483640152)
    On
    SensorEvent(sensor_id=1, ts=1466554964.325713, val=105.20052817504502)
    Off
    SensorEvent(sensor_id=1, ts=1466554965.330321, val=97.78633493089245)
    Off
    SensorEvent(sensor_id=1, ts=1466554966.333975, val=90.08049816341648)
    Off
    SensorEvent(sensor_id=1, ts=1466554967.338074, val=89.52641383841595)
    On
    SensorEvent(sensor_id=1, ts=1466554968.342416, val=101.35659321534875)
    ...

The scheduler calls the sensor's `_observe` method once every second. The events
are then dispatched to all the downstream subscribers. In the output,
we are seeing the On/Off output from the LED interleaved with the original
events printed by the `output` element we connected directly to the sensor.
Note that this will keep running forever, until you use Control-C to stop the
program.

Stopping the Scheduler
~~~~~~~~~~~~~~~~~~~~~~
As you saw in the last example, the `run_forever` method of the scheduler will
keep on calling publishers as long as any have been scheduled. If we are just
running a test, it would be nice to stop things rather than having to Control-C
out of the running program. We can do that by updating our sensor class to call
`_dispatch_completed` and then return `False` from the `_observe` method
after a specified number of events. This will tell the downstream elements and
the scheduler that we are done. The scheduler will then deschedule the sensor.
Since there are no other sensors scheduled, it will exit the `_run_forever`
loop, allowing the program to terminate. Here is the code for our revised
sensor::

    class RandomSensor(Publisher, DirectPublisherMixin):
        def __init__(self, sensor_id, mean, stddev, stop_after):
            """This sensor will signal it is completed after the
            specified number of events have been sampled.
            """
            super().__init__()
            self.sensor_id = sensor_id
            self.mean = mean
            self.stddev = stddev
            self.events_left = stop_after
    
        def _observe(self):
            """Sample the sensor and dispatch to the subscribers.
            """
            if self.events_left>0:
                evt = SensorEvent(self.sensor_id, time.time(),
                                  random.gauss(self.mean, self.stddev))
                self._dispatch_next(evt)
                self.events_left -= 1
                return True # more data potentially available
            else:
                # Reached the specified number of events. Tell the
                # downstream we are done.
                self._dispatch_completed()
                # By returning False, we tell the scheduler we are really
                # done and can be descheduled.
                return False
    
        def __str__(self):
            return "RandomSensor(%s, %s, %s)" % \
                (self.sensor_id, self.mean, self.stddev)

When we instantiate our sensor, we now pass in this additional parameter::

    sensor = RandomSensor(1, MEAN, STDDEV, stop_after=5)

When we run the example this time, the program stops after five samples::

    Off
    SensorEvent(sensor_id=1, ts=1466570049.852193, val=87.42239337997071)
    On
    SensorEvent(sensor_id=1, ts=1466570050.856118, val=114.47614678277142)
    Off
    SensorEvent(sensor_id=1, ts=1466570051.860044, val=90.26934530230736)
    On
    SensorEvent(sensor_id=1, ts=1466570052.864378, val=102.70094730226809)
    On
    SensorEvent(sensor_id=1, ts=1466570053.868465, val=102.65381015942252)
    LED Completed
    Calling unschedule hook for RandomSensor(1, 100, 10)
    No more active schedules, will exit event loop
    That's all folks!

Next Steps
----------
You have reached the end of the tutorial. To learn more, take a look at the code
under the `examples` directory. In particular, the Jupyter notebooks under
`examples/notebooks` will walk you interactively through more complex examples.
You can also read through the code in the `antevents` proper -- a goal of the
project is to ensure that it is clearly commented.


Design Issues
=============
We now discuss some open design issues. These will eventually be resolved and
then the discussion moved to another file (perhaps called "design decisions").
At the end of each issue, there is a line that indicates the current bias for
a decision, either **Keep as is** or **Change**.

Publishers, Sensors, and the Scheduler
--------------------------------------
Today, sensors are just a special kind of publisher. Depending on whether it is
intended to be blocking or non-blocking, it implements `_observe` or
`observe_and_enqueue`. The reasoning behind this was to make it impossible to
schedule a blocking sensor on the main thread. Perhaps this is not so important.
If we relaxed this restriction, we could move the dispatch logic to the
scheduler or the the base `Publisher` class.

This change would also allow a single publisher implementation to be used with
most sensors. We could then build a separate common interface for sensors,
perhaps modeled after the Adafruit Unified Sensor Driver
(https://github.com/adafruit/Adafruit_Sensor).

Bias: **Change**

Disposing of Subscriptions
--------------------------
In the current system, the `Publisher.subscribe` method returns a "dispose"
thunk that can be used to undo the subscription. This is modeled after the
`subscribe` method in Microsoft's Rx framework. Does this unnecessarily
complicate the design? Will real dataflows use this to change their structure
dynamically? If we eventually implement some kind of de-virtualization, it
would be difficult to support unsubscribing. Also, it might be more convenient
for `subscribe` to return either the subscribed object or the publisher, to
allow for method chaining like we do for filters (or is that going to be too
confusing?).

As an argument for keeping the dispose functionality, we may want to change
scheduled publisher elements so that, if they have no subscriptions, they are
unscheduled (or we could make it an option). That would make it easy to stop a
sensor after a certain number of calls by disposing of the subscription.

Bias: **Keep as is**

Terminology: Reader/Writer vs. Source/Sink
------------------------------------------
We introduced the *reader* and *writer* terms to refer to publishers that
introduce event streams into the system and subscribers that consume event
streams with no output, respectively. This was introduced to avoid confusion
when referring to adapters to external publish/subscribe systems (e.g. MQTT).
An element that subscribes to messages from an external queue is a *publisher*
in our system and an element that publishes messages to an external queue is a
*subscriber*. That is really confusing!

Reader/writer is better, but it might still be confusion that a reader is
injecting messages into an Ant Events dataflow. Perhaps the terms *source*
and *sink* would be more obvious. Is it worth the change?

Bias: **Change**

The `on_error` Callback
-----------------------
Borrowing from Microsoft's Rx framework, Ant Events has three callbacks on each
subscriber: `on_next`, `on_completed`, and `on_error`. The `on_error` callback
is kind of strange: since it is defined to be called *at most once*, it is
really only useful for fatal errors. A potentially intermittent sensor error
would have to to be propagated in-band (or via another topic in Ant Events).
In that case, what is the value of an `on_error` callback over just throwing a
fatal exception? Ant Events does provide a `FatalError` exception class. Relying
just on the `on_error` callbacks makes it too easy to accidently swallow a fatal
error.

There are two reasons I can think of for `on_error`:

1. Provide downstream components a chance to release resources. However, if we
   going to stop operation due to a fatal error, we would probably just want to
   call it for all active elements in the system (e.g. an unrelated element may
   need to save some internal state). We could let the system keep running, but
   that may lead to a zombie situation. It is probably better to fail fast and
   let some higher level component resolve the issue (e.g. via a process restart).
2. If a sensor fails, we may want to just keep running and provide
   best guess data going forward in place of that sensor. The `on_error`
   callback gives us the opportunity to do that without impacting the downstream
   elements. However, I am not sure how likely this use case is compared to the
   case where we have an intermittent error (e.g. a connection to a sensor node
   is lost, but we will keep retrying the connection).

 In general, error handling needs more experience and thought.

 Bias: **Change, but not sure what to**


Related Work
============
The architecture was heavily influenced by Microsoft's Rx_ (Reactive Extensions)
framework and the Click_ modular router. We started by trying to simplfy Rx for
the IoT case and remove some of the .NETisms. A key addition was the support for
multiple topics, which makes more complex dataflows possible.

.. _Rx: https://msdn.microsoft.com/en-us/data/gg577609.aspx
.. _Click: http://read.cs.ucla.edu/click/click



