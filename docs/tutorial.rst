.. _tutorial:

2. Tutorial
===========

To understand the core concepts in ThingFlow, let us build a simple app with a
dummy sensor that generates random data and feeds it to a dummy LED. The final
code for this example is at ``thingflow-python/examples/tutorial.py``.

Input Things and Output Things
------------------------------
Each ThingFlow "thing" is either an *output thing*, which
emits events and and puts the into the workflow, an *input thing*, which consumes
events, accepting event streams from the workflow, or both.

An output thing may create multiple output event streams. Each output stream is
associated with a named *output port*. Likewise, an input thing may accept
input streams via named *input ports*. Input and output ports form the basis
for interconnections in our data flows.

 In general, we can connect an input port to an output port via an
 output thing's ``connect()`` method like this::

    output_thing.connect(input_thing,
                         port_mapping=('output_port_name', 'input_port_name'))

There also exists a special *default* port, which is used when no port name
is specified on a connection. If you leave off the port mapping
parameter in the ``connect()`` call, it maps the default port of the
output to the default port of the input::

    output_thing.connect(input_thing)

Once connected through the ``connect`` call, a output and input thing interact
through three methods on the input thing:

* ``on_next``, which passes the next event in the stream to the input thing.
* ``on_error``, which should be called at most once, if a fatal error occurs. The
  exception that caused the error is passed as the parameter.
* ``on_completed``, which signals the end of the stream and takes no parameters.

Note that each output port may have multiple connections. The functionality
in the ``thingflow.base.OutputThing`` base class handles dispatching the
events to all downstream consumers.

More terms for specialized things
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We call things which have a default input port and a default output port *filters*.
Filters can be easily composed into pipelines. We talk more about filters
:ref:`below <filters>`. A number of filters are defined by ThingFlow under the
module ``thingflow.filters``.

Some things interface to outside world, connecting ThingFlow to
transports and data stores like MQTT,
PostgreSQL, and flat CSV files. We call these things *adapters*. Several may be
found under ``thingflow.adapters``. We call an output thing that emits events
coming from an outside source a *reader*. An input thing which accepts event
and conveys them to an outside system a *writer*.

Sensors
-------
Since ThingFlow is designed for Internet of Things applications, data capture
from sensors is an important part of most applications. To this end, ThingFlow
provides a *sensor* abstraction. A sensor is any python class that implements
a ``sample()`` method and has a ``sensor_id`` property. The ``sample()`` method
takes no arguments and returns the current value of the sensor. The ``sensor_id``
property is used to identify the sensor in downstream events. Optionally, a
sensor can indicate that there is no more data available by thowing a
``StopIteration`` exception.

To plug sensors into the world of input and output things, ThingFlow provides
the ``SensorAsOutputThing`` class. This class wraps any sensor, creating an
output thing. When the thing is called by the scheduler, it calls the sensor's ``sample()``
method, wraps the value in an event (either ``SensorEvent`` or a custom
event type), and pushes it to any connected input things. We will see
``SensorAsOutputThing`` in action below.

There are cases where this simple sensor abstraction is not sufficient to model
a real-life sensor or you are outputting events that are not coming directly
from a sensor (e.g. from a file or a message broker). In those situations,
you can just create your own output thing class, subclassing from the base
``OutputThing`` class.

Implementing a Sensor
~~~~~~~~~~~~~~~~~~~~~
Now, we will implement a simple test sensor that generates random values.
There is no base sensor class in ThingFlow, we just need a class that
provides a ``sensor_id`` property and a ``sample()`` method. We'll take
the ``sensor_id`` value as an argument to ``__init__()``. The sample
value will be a random number generated with a Gaussian distribution,
via ``random.gauss``. Here is the code for a simple version of our
sensor:

.. code-block:: python

    import random
    random.seed()
    
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
number of events:

.. code-block:: python
  
    import random
    random.seed()
    import time
    from thingflow.base import SensorAsOutputThing
    
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

Now, let's instantiate our sensor:

.. code-block:: python

    from thingflow.base import SensorAsOutputThing
    MEAN = 100
    STDDEV = 10
    sensor = SensorAsOutputThing(RandomSensor(1, MEAN, STDDEV, stop_after=5))


Implementing an Input Thing
---------------------------
Now, let us define a simple intput thing -- a dummy LED actuator. The LED will
inherit from the ``thingflow.base.IntputThing`` class, which defines the
input thing interface for receiving events on the default port. Here is the code:

.. code-block:: python

    from thingflow.base import InputThing
    class LED(InputThing):
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
instantiate an LED:

.. code-block:: python

    led = LED()

.. _filters:
   
Filters
-------
A *filter* is a thing that as a single default input port and a single default
output port. There is a base class for filters, ``thingflow.base.Filter``,
which subclasses from both ``InputThing`` and ``OutputThing``.
Although you can instantiate
filter classes directly, ThingFlow makes use of some Python metaprogramming
to dynamically add convenience methods to the base ``OutputThing`` class
to create and return filtes. This allows filters can be easily chained
together, implementing multi-step query pipelines without any glue code.

Let us now create a series of filters that connect together our dummy light
sensor and our LED. Here is some code to look at each event and send ``True`` to
the LED if the value exceeds the mean (provided to the sensor) and ``False``
otherwise:

.. code-block:: python

    import thingflow.filters.map
    sensor.map(lambda evt: evt.val > MEAN).connect(led)

The ``import`` statement loads the code for the ``map`` filter. By loading
it, it is added as a method to the ``OutputThing`` class. Since the sensor was
wrapped in ``SensorAsOutputThing``, which inherits from ``OutputThing``, it
gets this method as
well. Calling the method creates a filter which runs the supplied
anonymous function on each event. This
filter is automatically connected to the sensor's default output port.
The ``map`` call returns the filter, allowing it to be used
in chained method calls. In this case, we ``connect`` the ``led`` to the
filter's event stream.

Inside the Map filter
~~~~~~~~~~~~~~~~~~~~~
It is important to note that the call to a filter method returns a filter
object and not an event. This call happens at initializaiton time.
To get a better understanding of what's happening, let's take a look
inside the ``map`` filter.

First, let us create a straightfoward implementation of our filter
by subclassing from the base ``Filter`` class and then overridding
the ``on_next`` method:

.. code-block:: python

    from thingflow.base import Filter, filtermethod
    class MapFilter(Filter):
        def __init__(self, previous_in_chain, mapfun):
	    super().__init__(previous_in_chain)
	    self.mapfun = mapfun

	def on_next(self, x):
	    next = self.mapfun(x)
	    if next is not None:
	        self._dispatch_net(next)
	    

    @filtermethod(OutputThing)
    def map(this, mapfun):
        return MapFilter(this, mapfun)

In this case, the ``on_next`` method applies the provided ``mapfun``
mapping function to each incoming event and, if the result is not ``None``,
passes it on to the default output port via the method ``dispatch_next``
(whose implementation is inherited from the base ``OutputThing`` class).

In the ``__init__`` method of our filter, we accept a ``previous_in_chain``
argument and pass it to the parent class's constructor. As the name implies,
this argument should be the previous filter in the chain which is acting as
a source of events to this filter. ``Filter.__init__`` will perform a
``previous_in_chain.connect(self)`` call to establish the connection.

We can now wrap our filter in the function ``map``, which takes the previous
filter in the chain and our mapping function as arguments, returning a new
instance of ``MapFilter``. The decorator ``functionfilter`` is used to attach
this function to ``OutputThing`` as a method. We can then make calls
like ``thing.map(mapfun)``.

The actual code for ``map``in ThingFlow map be found in the module ``thingflow.filters.map``.
It is written slightly differently, in a more functional style:

.. code-block:: python

   from thingflow.base import OutputThing, FunctionFilter, filtermethod
   
   @filtermethod(OutputThing, alias="select")
   def map(this, mapfun):
       def on_next(self, x):
           y = mapfun(x)
           if y is not None:
               self._dispatch_next(y)
       return FunctionFilter(this, on_next, name='map')

The ``FunctionFilter`` class is a subclass of ``Filter`` which takes its ``on_next``,
``on_error``, and ``on_completed`` method implementations as function parameters.
In this case, we define ``on_next`` inside of our ``map`` filter. This avoids the
need to even create a ``MapFilter`` class.

Sensor Events
-------------
ThingFlow provides a *namedtuple* called ``thingflow.base.SensorEvent``, to
serve as elements of our data stream. The first member of the tuple, called
``sensor_id`` is the sensor id property of the sensor from which the event
originated. The second member of the event tuple, ``ts``, is a timestamp
of when the event was generated. The third member, ``val``, is the value
returned by the sensor's ``sample()`` method.

The ``SensorAsOutputThing`` wrapper class creates ``SensorEvent`` instances by default.
However, you can provide an optional ``make_sensor_event`` callback to
``SensorAsOutputThing`` to override this behavior and provide your own event types.

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
an event dataflow.  First, can add an ``output`` thing to various points in the
flow. The ``output`` thing just prints each event that it see. It is another
filter that can be added to the base ``OutputThing`` class by importing the
associated Python package. For example, here is how we add it as a connection to
our sensor, to print out every event the sensor emits::

    import thingflow.filters.output
    sensor.output()

Note that this does not actually print anything yet, we have to run the
*scheduler* to start up our dataflow and begin sampling events from the sensor.

Another useful debugging tool is the ``print_downstream`` method on
``OutputThing``. It can be called on any subclass to see a representation
of the event tree rooted at the given thing. For example, here is what we
get when we call it on the ``sensor`` at this point::

    ***** Dump of all paths from RandomSensor(1, 100, 10) *****
      RandomSensor(1, 100, 10) => select => LED
      RandomSensor(1, 100, 10) => output
    ************************************

Finally, the ``OutputThing`` class also provices a ``trace_downstream`` method.
It will instument (transitively) all downstream connections. When the scheduler
runs the thing, all events passing over these connections will be printed.

The Scheduler
-------------
As you can see, it is easy to create these pipelines. However, this sequence of
things will do nothing until we hook it into the main
event loop. In particular, any output thing that source events into the system
(e.g. sensors) must be made known to the *scheduler*. Here is an example where
we take the dataflow rooted at the light sensor, tell the scheduler to sample it
once every second, and then start up the event loop:

.. code-block:: python

    import asyncio
    from thingflow.base import Scheduler
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

The scheduler calls the ``_observe`` method of ``SensorAsOutputThing`` once every second.
This method samples the sensor and calls ``_dispatch_next`` to pass it to
any downstream things connected to the output port.
In the program output above,
we are seeing the On/Off output from the LED interleaved with the original
events printed by the ``output`` element we connected directly to the sensor.
Note that this will keep running forever, until you use Control-C to stop the
program.

Stopping the Scheduler
~~~~~~~~~~~~~~~~~~~~~~
As you saw in the last example, the ``run_forever`` method of the scheduler will
keep on calling things as long as any have been scheduled. If we are just
running a test, it would be nice to stop the program automatically
ather than having to Control-C
out of the running program. Our sensor class addresses this by including an
optional ``stop_after`` parameter on the constuctor. When we instantiate our
sensor, we can pass in this additional parameter::

    sensor = SensorAsOutputThing(RandomSensor(1, MEAN, STDDEV, stop_after=5))

The scheduler's ``run_forever()`` method does not really run forever -- it only
runs until there are no more schedulable actions. When our sensor throws the
``StopIteration`` exception, it causes the wrapping ``SensorAsOutputThing`` to deschedule
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

* Continue with this documentation. In the :ref:`next section <output_things>`,
  we look at implementing output things.
* Take a look at the code under the ``examples`` directory.
* You can also read through the code in the ``thingflow`` proper -- a goal of the
  project is to ensure that it is clearly commented.

