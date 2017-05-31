.. _ports:

4. Things with Non-default Ports
================================

ThingFlow provides a general dataflow architecture. Output things can
output events on different ports and input things can receive messages via
different ports. Each ``connect()`` call can rename ports, allowing the
interconnection of any compatible ports. For example, one might have code like::

    output_thing.connect(input_thing,
                         port_mapping=('out_port_name', 'in_port_name'))

As you know, ThingFlow provides a special ``default`` port that does not need
any mapping. This makes it convenient for building chains of filters and is good
enough most of the time. However, when you need a more complex data flow, the
more general mapping capability can be very helpful. We will now look at it in
more detail.

Multiple Output Ports
---------------------
To create an output thing which sends messaages on multiple output ports,
one subclasses from ``OutputThing`` or one of its descendents. Here is a simple
thing that accepts events on the default input port and sends values to one or
more of three ports:

.. code-block:: python

    class MultiPortOutputThing(OutputThing, InputThing):
        def __init__(self, previous_in_chain):
            super().__init__(ports=['divisible_by_two', 'divisible_by_three',
                                     'other'])
            # connect to the previous filter
            self.disconnect_from_upstream = previous_in_chain.connect(self)
            
        def on_next(self, x):
            val = int(round(x.val))
            if (val%2)==0:
                self._dispatch_next(val, port='divisible_by_two')
            if (val%3)==0:
                self._dispatch_next(val, port='divisible_by_three')
            if (val%3)!=0 and (val%2)!=0:
                self._dispatch_next(val, port='other')
    
        def on_completed(self):
            self._dispatch_completed(port='divisible_by_two')
            self._dispatch_completed(port='divisible_by_three')
            self._dispatch_completed(port='other')
            
        def on_error(self, e):
            self._dispatch_error(e, port='divisible_by_two')
            self._dispatch_error(e, port='divisible_by_three')
            self._dispatch_error(e, port='other')


In the ``_init__`` constructor, we must be sure to call the super class's
constructor, passing it the list of ports that will be used. If the list is
not provided, it is initialized to the default port, and sending to any other
port would be a runtime error.

This thing will accept events from the default input port, so we subclass from
``InputThing`` and process sensor values in the ``on_next()`` method.
We first obtain a value from the event and round it
to the nearest integer. Next, we see if it is divisible by 2. If so, we call
``_dispatch_next()`` to dispatch the value to the ``divisible_by_two`` port,
passing the port name as the second parameter (it defaults to ``default``).
Next, we check for divisibity by three, and dispatch the value to the
``divisible_by_three`` port if it is divisible. Note that a number like six
will get dispatched to both ports. Finally, if the value is not divisible by
either two or three, we dispatch it to the ``other`` port.

For the ``on_completed()`` and ``on_error()`` events, we forward the
notifications to each of the output ports, by calling ``_dispatch_completed()``
and ``_dispatch_next()`` three times. In general, each port can be viewed as
a separate event stream with its own state. An output thing might decide to
mark completed a subset of its ports while continuing to send new events
on other ports.

Let us look at how this thing might be called:

.. code-block:: python

    sensor = SensorAsOutputThing(RandomSensor(1, mean=10, stddev=5,
                                              stop_after_events=10))
    mtthing = MultiPortOutputThing(sensor)
    mtthing.connect(lambda v: print("even: %s" % v),
                    port_mapping=('divisible_by_two', 'default'))
    mtthing.connect(lambda v: print("divisible by three: %s" % v),
                    port_mapping=('divisible_by_three', 'default'))
    mtthing.connect(lambda v: print("not divisible: %s" % v),
                    port_mapping=('other', 'default'))
    scheduler.schedule_recurring(sensor)
    scheduler.run_forever()

Here, we map a different anonymous print function to each output port of the
thing. Internally, ``connect`` is wrapping the anonymous functions with
``CallableAsInputThing``. This thing only listens on a default port, so we
have to map the port names in the ``connect()`` calls.

The full code for this example is at ``examples/multi_port_example.py``.

Multiple Input Ports
--------------------
Now, let us consider a thing that supports incoming messages on multiple
ports. Messages on non-default input ports are passed to different methods on an
input thing. Specifically, given a port name ``PORT``, events are dispatched
to the method ``on_PORT_next()``, completion of the port's stream is
dispatched to ``on_PORT_completed()``, and errors are dispatched to
``on_PORT_error()``. Multiple ports are frequently useful
when implementing state machines or filters that combine multiple inputs.

As an example, assume that we have a state machine that reads data
from two sensors: a *left* sensor and a *right* sensor. Here is how the code
might be structured:

.. code-block:: python

    class StateMachine:
        def on_left_next(self, x):
	    ...
	def on_left_completed(self):
	    ...
	def on_left_error(self):
	    ...
        def on_right_next(self, x):
	    ...
	def on_right_completed(self):
	    ...
	def on_right_error(self):
	    ...

Here is how we might set up the connections to the sensors:

.. code-block:: python

    left = SensorAsOutputThing(LuxSensor('left'))
    right = SensorPsOutputThing(LuxSensor('right'))
    state_machine = StateMachine()
    left.connect(state_machine, port_mapping=('default', 'left'))
    right.connect(state_machine, port_mapping=('default', 'right'))

Each sensor outputs its data on the default port, so we map the connections
to the ``left`` and ``right`` ports on the state machine.

Multi-port Filters
-------------------
A *filter* is an ThingFlow element that has both default input and default
output ports. Filters can be easily connected into pipelines.
Filters usually have a single input port and a single output port, but other
topologies are possible (typically one-to-many or many-to-one). One particularly
useful filter is the *dispatcher*. A dispatcher routes each incoming event
(on the default input port) to one of several output ports, based on some
criteria.

For example, consider the filter ``thingflow.filters.dispatch.Dispatcher``. This
filter is provided a set of routing rules in the form of (predicate function,
output port) pairs. An output port is created for each rule (plus the default
port). In the ``on_next()`` method of the filter's InputThing interface, an
incoming event is tested on each of the predicate functions in order. When a
predicate is found that returns true, the event is dispatched to the associated
port and the rule search stops for that event. If an event fails all the
predicate checks, it is passed to the ``default`` port.

Here is the most relevant parts of the filter code (see ``dispatch.py`` for the
complete code):

.. code-block:: python

    class Dispatcher(OutputThing, InputThing):
        def __init__(self, previous_in_chain, dispatch_rules):
            ports = [port for (pred, port) in dispatch_rules] + ['default']
            super().__init__(ports=ports)
            self.dispatch_rules = dispatch_rules
            self.disconnect = previous_in_chain.connect(self)
    
        def on_next(self, x):
            for (pred, port) in self.dispatch_rules:
                if pred(x):
                    self._dispatch_next(x, port=port)
                    return
            self._dispatch_next(x, port='default') # fallthrough case

We will use this dispatcher within a larger example in the subsection :ref:`solar-water-heater`.


