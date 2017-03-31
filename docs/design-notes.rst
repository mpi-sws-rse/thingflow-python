.. _design:

7. Design Notes
===============

This section describes some design decisions in the ThingFlow API
that are or were under discussion.

Closed Issues
-------------
These issues have already been decided, and any recommended changes implemented
in the ThingFlow API. The text for each issue still uses the future tense,
but we provide the outcome of the decision at the end of each section.

Basic Terminology
~~~~~~~~~~~~~~~~~
The terminology has evolved twice, once from the original *observer* and
*observable* terms used by Mirosoft's RxPy to *subscribers* and *publishers*.
Our underling communication model is really an internal publish/subscribe
between the "things". This was the terminology used in our AntEvents framework.

We still found that a bit confusing and changed to the current terminology
of *input things* and *output things*. Rather than topics, we have ports, which
are connected rather than subscribed to. We think this better reflects the
dataflow programming style.

** Outcome**: Changed

Output Things, Sensors, and the Scheduler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Today, sensors are just a special kind of output thing. Depending on whether it is
intended to be blocking or non-blocking, it implements ``_observe`` or
``observe_and_enqueue``. The reasoning behind this was to make it impossible to
schedule a blocking sensor on the main thread. Perhaps this is not so important.
If we relaxed this restriction, we could move the dispatch logic to the
scheduler or the the base ``OutputThing`` class.

This change would also allow a single output thing implementation to be used with
most sensors. We could then build a separate common interface for sensors,
perhaps modeled after the Adafruit Unified Sensor Driver
(https://github.com/adafruit/Adafruit_Sensor).

**Outcome**: Changed

We created the *sensor* abstraction and the ``SensorAsOutputThing`` wrapper class to
adapt any sensor to the output thing API. We left the original output thing API,
as there are still cases (e.g. adapters) that do not fit into the sensor
sampling model.

Open Issues
-----------
At the end of each issue, there is a line that indicates the current bias for
a decision, either **Keep as is** or **Change**.

Disconnecting
~~~~~~~~~~~~~
In the current system, the ``OutputThing.connect`` method returns a "disconnect"
thunk that can be used to undo the connection. This is modeled after the
``subscribe`` method in Microsoft's Rx framework. Does this unnecessarily
complicate the design? Will real dataflows use this to change their structure
dynamically? If we eventually implement some kind of de-virtualization, it
would be difficult to support disconnecting. Also, it might be more convenient
for ``connect`` to return either the connected object or the output thing, to
allow for method chaining like we do for filters (or is that going to be too
confusing?).

As an argument for keeping the disconnect functionality, we may want to change
scheduled output things so that, if they have no connections, they are
unscheduled (or we could make it an option). That would make it easy to stop a
sensor after a certain number of calls by disconnecting from it.

Bias: **Keep as is**

Terminology: Reader/Writer vs. Source/Sink
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We introduced the *reader* and *writer* terms to refer to output things that
introduce event streams into the system and input things that consume event
streams with no output, respectively.
A thing that accepts messages from an external source is a *output thing*
in our system and an thing that emits messages to an external distination is an
*input thing*. That is really confusing!

Reader/writer is better, but it might still be confusion that a reader is
injecting messages into an ThingFlow dataflow. Perhaps the terms *source*
and *sink* would be more obvious. Is it worth the change?

Bias: **Keep as is**

The ``on_error`` Callback
~~~~~~~~~~~~~~~~~~~~~~~~~
Borrowing from Microsoft's Rx framework, ThingFlow has three callbacks on each
subscriber: ``on_next``, ``on_completed``, and ``on_error``. The ``on_error`` callback
is kind of strange: since it is defined to be called *at most once*, it is
really only useful for fatal errors. A potentially intermittent sensor error
would have to to be propagated in-band (or via another topic in ThingFlow).
In that case, what is the value of an ``on_error`` callback over just throwing a
fatal exception? ThingFlow does provide a ``FatalError`` exception class. Relying
just on the ``on_error`` callbacks makes it too easy to accidently swallow a fatal
error.

There are two reasons I can think of for ``on_error``:

1. Provide downstream components a chance to release resources. However, if we
   going to stop operation due to a fatal error, we would probably just want to
   call it for all active things in the system (e.g. an unrelated thing may
   need to save some internal state). We could let the system keep running, but
   that may lead to a zombie situation. It is probably better to fail fast and
   let some higher level component resolve the issue (e.g. via a process restart).
2. If a sensor fails, we may want to just keep running and provide
   best guess data going forward in place of that sensor. The ``on_error``
   callback gives us the opportunity to do that without impacting the downstream
   things. However, I am not sure how likely this use case is compared to the
   case where we have an intermittent error (e.g. a connection to a sensor node
   is lost, but we will keep retrying the connection).

In general, error handling needs more experience and thought.

Bias: **Change, but not sure what to**

Related Work
------------
The architecture was heavily influenced by Microsoft's Rx_ (Reactive Extensions)
framework and the Click_ modular router. We started by trying to simplfy Rx for
the IoT case and remove some of the .NETisms. A key addition was the support for
multiple ports, which makes more complex dataflows possible.

.. _Rx: https://msdn.microsoft.com/en-us/data/gg577609.aspx
.. _Click: http://read.cs.ucla.edu/click/click
