.. _functional:

5. Functional API
=================

Motivation
----------
The primary API that ThingFlow provides for filters is a *fluent* API based
on the concept of *method chaining*: each filter method on the ``OutputThing``
base class returns the last thing in the connection chain. This
result can then be used for subsequent calls. For example, to apply a
filter followed by a map, we might say::

    thing.filter(lambda evt: evt.val > 300).map(lambda evt:evt.val)

Underneath the covers, the ``filter()`` call returns a ``Filter`` object
(a subclass of ``OutputThing``). The ``map()`` method call is then made
against this object.

This approach is convenient when your processing pipeline really is a
straight line. If you have parallel branches, or more complex structures,
you end up having to break it up with assignment statements. For example,
consider the following dataflow, based on the code in
``examples/rpi/lux_sensor_example.py``:

.. code-block:: python

    lux = SensorPub(LuxSensor())
    lux.output()
    lux.csv_writer(os.path.expanduser('~/lux.csv'))
    actions = lux.map(lambda event: event.val > threshold)
    actions.subscribe(GpioPinOut())
    actions.subscribe(lambda v: print('ON' if v else 'OFF'))
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_periodic_on_separate_thread(lux, interval)
    scheduler.run_forever()

In the above code, ``lux`` has three subscribers, and the output of the ``map``
filter has two subscribers.

Functional API
--------------
To simplfy these cases, we provide a *functional* API that can be used in
place of (or along with) the *fluent* API. For each method added to the
thing via the ``@filtermethod`` decorator (in ``thingflow.base``), a
function with the same name is added to the module containing the definition
(e.g. ``thingflow.filters.output`` has an ``output`` function and
``thingflow.filters.map`` has ``map`` and ``select`` functions). These functions
take all the parameters of the associated method call (except for the implied
``self`` parameter of a bound method) and return what we call a *thunk*.
In this case, a thunk is a function that accepts exactly one parameter, a
output thing. The thunk subscribes one or more fitlers to the output thing and, if
further downstream connections are permitted, returns the last filter in the
chain. When composing filters, thunks can be used as follows:

1. The ``Schedule`` class has ``schedule_sensor()`` and
   ``schedule_sensor_on_separate_thread()`` methods. These take a
   sensor, wrap it in a ``SensorAsOutputThing`` instance, and then connect a sequence
   of filters to the output thing. Each filter can be passed in directly or
   passed indirectly via thunks.
2. The module ``thingflow.filters.combinators`` defines several functions that
   can be used to combine filters and thunks. These include ``compose``
   (sequential composition), ``parallel`` (parallel composition), and
   ``passthrough`` (parallel composition of a single spur off the main chain).

Example
-------
Now, let us look at the lux sensor example, using the functional API [1]_:

.. code-block:: python
		
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_sensor(lux, interval,
                              passthrough(output()),
                              passthrough(csv_writer('/tmp/lux.csv')),
                              map(lambda event:event.val > THRESHOLD),
			      passthrouh(lambda v: print('ON' if v else 'OFF')),
                              GpioPinOut())
    scheduler.run_forever()
    
Notice that we do not need to instantiate any intermediate variables. Everything
happens in the ``schedule_sensor()`` call. The first argument to this call is
the sensor (without being wrapped in ``SensorAsOutputThing``) and the second argument
is the sample interval. The rest of the arguments are a sequence of filters
and thunks to be called. Using a bit of ASCII art, the graph created looks as
follows::

            output
           /
  LuxSensor - csv_writer
          \
           map - lambda v: print(...)
	     \
	      GpioPinOut

The lux sensor has three connections: ``output``, ``csv_writer``, and ``map``.
We get this fanout by using the ``passthrough`` combinator, which creates a
spur off the main chain. A ``passthrough`` is then used with the output of
the ``map``, with the main chain finally ending at ``GpioPinOut``.

.. [1] A full, self-contained version of this example may be found at
       ``examples/functional_api_example.py``.

Combining the Fluent and Functional APIs
----------------------------------------
You can use the functional API within a fluent API method chain. For example,
let us include a sequence of filters in a ``passthrough()``:

.. code-block:: python

    sensor = SensorAsOutputThing(LuxSensor())
    sensor.passthrough(compose(map(lambda event:event.val>THRESHOLD), output()))\
          .csv_writer('/tmp/lux.csv')

Here, we used ``compose`` to build a sequence of ``map`` followed by ``output``.
Note that the final ``csv_writer`` call is run against the original events
output by the sensor, not on the mapped events. Here is the resuting
graph::

            map - output
           /
  LuxSensor - csvwriter

Internals
---------
The linq-style functions of the fluent API are defined to be
a kind of extension method -- their first parameter, usually named ``this``, is
the output thing on which the method will eventually be attached (to borrow
Smalltalk terminology, the "receiver"). The function
takes zero or more additional parameters and returns a ``Filter`` object to be
used for further chaining.

The decorator ``thingflow.base.filtermethod`` adds a linq-function as a method
on a base class (usually ``OutputThing``), effectively binding the ``this``
parameter and, thus, the receiver. To support the functional API, the
``filtermethod`` decorator also wraps the linq-function in a
``_ThunkBuilder`` object. This object, when called with
the parameters intended for our linq-function, returns a *thunk* -- a function
that has all parameters bound except the ``this`` receiver. When a thunk is
called (passing a output thing as a parameter), it calls the original linq-function
with the output thing as the ``this`` receiver and the rest of the parameters
coming from the original ``_ThunkBuilder`` call.

The functional API also needs some special handling in cases where we may make
``connect`` calls under the covers (e.g. the ``Scheduler.schedule_sensor()``
method or the various combinators in ``thingflow.filters.combinators``). Depending
on whether the input thing being passed in is a filter, a thunk, a thunk-builder,
or a plain function, we need to handle it differently. For example, if we are
given a filter ``f``, we can connect it to our receiver ``this`` via
``this.connect(f)``. However, if we are given a thunk ``t``, we achieve the
same thing via ``t(this)``. All of this logic is cenralized in
``thingflow.base._subscribe_thunk``.



