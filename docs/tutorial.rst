==================
AntEvents Tutorial
==================

To understand the core concepts in Ant Events, let us build a simple app with a
dummy sensor that generates random data and feeds it to a dummy LED. The final
code for this example is at ``antevents-python/examples/tutorial.py``.

Publishers and Subscribers
--------------------------
First a little background on two of the core abstractions in Ant Events.
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
publisher's ``subscribe()`` method like this::

    publisher.subscribe(subscriber,
                        topic_mapping=('pub_topic_name', 'sub_topic_name'))

There also exists a special *default* topic, which is used when no topic
is specified on a subscription. If you leave off the topic mapping
parameter in the subscribe call, it maps the default topic of the
publisher to the default topic of the subscriber::

    publisher.subscribe(subscriber)

Once connected through the subscribe call, a publisher and subscriber interact
through three methods on the subscriber:

* ``on_next``, which passes the next event in the stream to the subscriber.
* ``on_error``, which should be called at most once, if a fatal error occurs. The
  exception that caused the error is passed as the parameter.
* ``on_completed``, which signals the end of the stream and takes no parameters.

Internally, each publisher implements an ``_observe()`` method that gets one
event and dispatches it to its subscribers. This ``_observe()`` method is
called periodically by the *scheduler*, described in more detail below.

Sensors
-------
Since AntEvents is designed for Internet of Things applications, data capture
from sensors is an important part of most applications. To this end, AntEvents
provides a *sensor* abstraction. A sensor is any python class that implements
a ``sample()`` method and has a ``sensor_id`` property. The ``sample()`` method
takes no arguments and returns the current value of the sensor. The ``sensor_id``
property is used to identify the sensor in downstream events. Optionally, a
sensor can indicate that there is no more data available by thowing a
``StopIteration`` exception.

To plug sensors into the world of publishers and subscribers, AntEvents provides
the ``SensorPub`` class. This class wraps any sensor, creating a publisher.
When the publisher is called by the scheduler, it calls the sensor's ``sample()``
method, wraps the value in an event (either ``SensorEvent`` or a custom
event type), and pushes it to subscribers. We will see ``SensorPub`` in action
below.

There are cases where this simple sensor abstraction is not sufficient to model
a real-life sensor or you are publishing events that are not coming directly
from a sensor (e.g. from a file or a message broker). In those situations,
you can just create your own publisher class, subclassing from the base
``Publisher`` class.

Implementing a Sensor
~~~~~~~~~~~~~~~~~~~~~
Now, we will implement a simple test sensor that generates random values.
There is no base sensor class in AntEvents, we just need a class that
provides a ``sensor_id`` property and a ``sample()`` method. We'll take
the ``sensor_id`` value as an argument to ``__init__()``. The sample
value will be a random number generated with a Gaussian distribution,
via ``random.gauss``. Here is the code for a simple version of our
sensor::

    import random
    random.seed()
    import time
    from antevents.base import SensorPub
    
    class RandomSensor:
        def __init__(self, sensor_id, mean, stddev):
            """Generate a random value each time sample() is
	    called, using the specified mean and standard
	    deviation.
            """
            self.sensor_id = sensor_id
            self.mean = mean
            self.stddev = stddev
    
        def sample(self):
            return random.gauss(self.mean, self.stddev)
            
        def __str__(self):
            return "RandomSensor(%s, %s, %s)" % \
                (self.sensor_id, self.mean, self.stddev)

This sensor will generate a new random value each time it is called. If we
run it with a scheduler, it will run forever (at least until the program
is interrupted via Control-C). For testing, it would be helpful to stop
the program after a certain number of events. We can do that, by passing
an event limit to the constructor, counting down the events, and throwing
a ``StopIteration`` exception when the limit has been reached. Here is
an improved version of our sensor that can signal a stop after the specified
number of events::
  
    import random
    random.seed()
    import time
    from antevents.base import SensorPub
    
    class RandomSensor:
        def __init__(self, sensor_id, mean, stddev, stop_after):
            """This sensor will signal it is completed after the
            specified number of events have been sampled.
            """
            self.sensor_id = sensor_id
            self.mean = mean
            self.stddev = stddev
            self.events_left = stop_after
    
        def sample(self):
            if self.events_left>0:
                data = random.gauss(self.mean, self.stddev)
                self.events_left -= 1
                return data
            else:
                raise StopIteration
            
        def __str__(self):
            return "RandomSensor(%s, %s, %s)" % \
                (self.sensor_id, self.mean, self.stddev)

Now, let's instantiate our sensor::

    MEAN = 100
    STDDEV = 10
    sensor = SensorPub(RandomSensor(1, MEAN, STDDEV, stop_after=5))


Implementing an Subscriber
--------------------------
Now, let us define a simple subscriber -- a dummy LED actuator. The LED will
inherit from the ``antevents.base.DefaultSubscriber`` class, which defines the
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

As you can see, the main logic is in ``on_next`` -- if the event looks like a
true value, we just print "On", otherwise we print "Off". We won't do anything
special for the ``on_error`` and ``on_completed`` callbacks. Now, we can
instantiate an LED::

    led = LED()

Filters
-------
A *filter* is a component that accepts a single
input event stream on the default topic and outputs a single event stream on the
default topics. Through Python package imports and some Python metaprogramming,
you can dynamically add various convenience methods to the ``Publisher`` base
class that create and return filters. This allows filters can be easily chained
together, implementing multi-step query pipelines without any glue code.

Let us now create a series of filters that connect together our dummy light
sensor and our LED. Here is some code to look at each event and send ``True`` to
the LED if the value exceeds the mean (provided to the sensor) and ``False``
otherwise::

    import antevents.linq.select
    sensor.select(lambda evt: evt.val > MEAN).subscribe(led)

The ``import`` statement loads the code for the ``select`` filter. By loading
it, it is added as a method to the ``Publisher`` class. Since the sensor is a
``RandomSensor``, which inherits from ``Publisher``, it gets this method as
well. Calling the method creates a filter element which runs the supplied
anonymous function on each event and passes the result to its subscribers. This
filter is automatically subscribed to the ``sensor`` element's default event
stream. The ``select`` call returns the filter element, allowing it to be used
in chained method calls. In this case, we ``subscribe`` the ``led`` to the
filter's event stream.

SensorEvent
-----------
AntEvents provides a *namedtuple* called ``antevents.base.SensorEvent``, to
serve as elements of our data stream. The first member of the tuple, called
``sensor_id`` is the sensor id property of the sensor from which the event
originated. The second member of the event tuple, ``ts``, is a timestamp
of when the event was generated. The third member, ``val``, is the value
returned by the sensor's ``sample()`` method.

The ``SensorPub`` wrapper class creates ``SensorEvent`` instances by default.
However, you can provide an optional ``make_sensor_event`` callback to
``SensorPub`` to override this behavior and provide your own event types.

Sensor Output Example
---------------------
Imagine that the sensor defined above outputs the following three events,
separated by 10 seconds each::

    SensorEvent(1, 2016-06-21T17:43:25, 95)
    SensorEvent(1, 2016-06-21T17:43:35, 101)
    SensorEvent(1, 2016-06-21T17:43:45, 98)

The ``select`` filter would output the following::

    False
    True
    False

The LED would print the following::

    Off
    On
    Off

Some Debug Output
-----------------
There are a number of approaches one can take to help understand the behavior of
an event dataflow.  First, can add an ``output`` element to various points in the
flow. The ``output`` element just prints each event that it see. It is another
linq-style filter that can be added to the base publisher class by importing the
associated Python package. For example, here is how we add it as a subscriber to
our sensor, to print out every event the sensor emits::

    import antevents.linq.output
    sensor.output()

Note that this does not actually print anything yet, we have to run the
*scheduler* to start up our dataflow and begin sampling events from the sensor.

Another useful debugging tool is the ``print_downstream`` method on the
``Publisher``. It can be called on any publisher subclass to see a representation
of the event tree rooted at the given publisher. For example, here is what we
get when we call it on the ``sensor`` at this point::

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

The scheduler calls the sensor's ``_observe`` method once every second. The events
are then dispatched to all the downstream subscribers. In the output,
we are seeing the On/Off output from the LED interleaved with the original
events printed by the ``output`` element we connected directly to the sensor.
Note that this will keep running forever, until you use Control-C to stop the
program.

Stopping the Scheduler
~~~~~~~~~~~~~~~~~~~~~~
As you saw in the last example, the ``run_forever`` method of the scheduler will
keep on calling publishers as long as any have been scheduled. If we are just
running a test, it would be nice to stop things rather than having to Control-C
out of the running program. Our sensor class addresses this by including an
optional ``stop_after`` parameter on the constuctor. When we instantiate our
sensor, we can pass in this additional parameter::

    sensor = SensorPub(RandomSensor(1, MEAN, STDDEV, stop_after=5))

The scheduler's ``run_forever()`` method does not really run forever -- it only
runs until there are no more schedulable actions. When our sensor throws the
``StopIteration`` exception, it causes the wrapping ``SensorPub`` to deschedule
the sensor. At that point, there are no more publishers being managed by
the scheduler, so it exits the loop inside ``run_forever()``.

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
You have reached the end of the tutorial. To learn more, you might:

* Read the additional documents in this directory.
* Take a look at the code under the ``examples`` directory.
* You can also read through the code in the ``antevents`` proper -- a goal of the
  project is to ensure that it is clearly commented.

