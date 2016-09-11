=============
Design Issues
=============

This document describes some design decisions in the AntEvents API
that are or were under discussion.

Open Issues
===========
At the end of each issue, there is a line that indicates the current bias for
a decision, either **Keep as is** or **Change**.

Disposing of Subscriptions
--------------------------
In the current system, the ``Publisher.subscribe`` method returns a "dispose"
thunk that can be used to undo the subscription. This is modeled after the
``subscribe`` method in Microsoft's Rx framework. Does this unnecessarily
complicate the design? Will real dataflows use this to change their structure
dynamically? If we eventually implement some kind of de-virtualization, it
would be difficult to support unsubscribing. Also, it might be more convenient
for ``subscribe`` to return either the subscribed object or the publisher, to
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

Bias: **Keep as is**

The ``on_error`` Callback
--------------------------
Borrowing from Microsoft's Rx framework, Ant Events has three callbacks on each
subscriber: ``on_next``, ``on_completed``, and ``on_error``. The ``on_error`` callback
is kind of strange: since it is defined to be called *at most once*, it is
really only useful for fatal errors. A potentially intermittent sensor error
would have to to be propagated in-band (or via another topic in Ant Events).
In that case, what is the value of an ``on_error`` callback over just throwing a
fatal exception? Ant Events does provide a ``FatalError`` exception class. Relying
just on the ``on_error`` callbacks makes it too easy to accidently swallow a fatal
error.

There are two reasons I can think of for ``on_error``:

1. Provide downstream components a chance to release resources. However, if we
   going to stop operation due to a fatal error, we would probably just want to
   call it for all active elements in the system (e.g. an unrelated element may
   need to save some internal state). We could let the system keep running, but
   that may lead to a zombie situation. It is probably better to fail fast and
   let some higher level component resolve the issue (e.g. via a process restart).
2. If a sensor fails, we may want to just keep running and provide
   best guess data going forward in place of that sensor. The ``on_error``
   callback gives us the opportunity to do that without impacting the downstream
   elements. However, I am not sure how likely this use case is compared to the
   case where we have an intermittent error (e.g. a connection to a sensor node
   is lost, but we will keep retrying the connection).

In general, error handling needs more experience and thought.

Bias: **Change, but not sure what to**

Closed Issues
=============
These issues have already been decided, and any recommended changes implemented
in the AntEvents API. The text for each issue still uses the future tense,
but we provide the outcome of the decision at the end of each section.

Publishers, Sensors, and the Scheduler
--------------------------------------
Today, sensors are just a special kind of publisher. Depending on whether it is
intended to be blocking or non-blocking, it implements ``_observe`` or
``observe_and_enqueue``. The reasoning behind this was to make it impossible to
schedule a blocking sensor on the main thread. Perhaps this is not so important.
If we relaxed this restriction, we could move the dispatch logic to the
scheduler or the the base ``Publisher`` class.

This change would also allow a single publisher implementation to be used with
most sensors. We could then build a separate common interface for sensors,
perhaps modeled after the Adafruit Unified Sensor Driver
(https://github.com/adafruit/Adafruit_Sensor).

**Outcome**: Changed

We created the *sensor* abstraction and the ``SensorPub`` wrapper class to
adapt any sensor to the publisher API. We left the original publisher API,
as there are still cases (e.g. adapters) that do not fit into the sensor
sampling model.
