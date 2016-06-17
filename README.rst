===========
Ant Events
===========

Introduction
============
Ant Events is a (Python3) framework for building IOT event
processing dataflows. Components which represent processing steps on an
event stream can be combined together to implement complex and distributed
event processing workflows. Each processing step is either a *publisher*, which
sources events and and puts the into the workflow, a *subscriber*, which sinks
events, accepting event streams from the workflow, or both.

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

A *filter* is a component that accepts a single
input event stream on the default topic and outputs a single event stream on the
default topics. Through Python package imports and some Python metaprogramming,
you can dynamically add various convenience methods to the `Publisher` base
class that create and return filters. This allows filters can be easily chained
together, implementing multi-step query pipelines without any glue code.
For example, the following code takes a lux sensor (a publisher),
extracts the sensor value field from a more complex structure (via `select()`),
takes the running average of this value over the last five samples, outputs a
boolean whether this value exceeds a threshold (via `map`), and uses this
boolean value to control an LED (via the hardware GPIO bus)::

    lux = LuxSensor()
    lux.select(lambda e: e.val).running_avg(5) \
       .map(lambda v: v > threshold).GpioPinOut()

As you can see, it is easy to create these pipelines. However, this sequence of
publishers and subscribers will do nothing until we hook it into the main
event loop. In particular, any publishers that source events into the system
(e.g. sensors) must be made known to the *scheduler*. Here is an example where
we take our lux sensor, tell the scheduler to sample it once every two seconds,
and then start up the event loop::

    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_periodic(lux, 2)
    scheduler.run_forever()


