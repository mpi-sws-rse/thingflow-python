========================
Publish/Subscribe Topics
========================

AntEvents provides a general publish-subscriber architecture. Publishers can
publish events on different topics and each subscription is for a specific
topic. A topic published by a given publisher may be mapped to any topic name by
its subscribers. For example, one might have code like::

    publisher.subscribe(subscriber,
                        topic_mapping=('pub_topic_name', 'sub_topic_name'))

As you know, AntEvents provides a special ``default`` topic that does not need
any mapping. This makes it convenient for building chains of filters and is good
enough most of the time. However, when you need a more complex data flow, the
more general mapping capability can be very helpful. We will now look at it in
more detail.

Publishing to Multiple Topics
-----------------------------
To create a publisher which outputs on multiple topics, one subclasses from the
``Publisher`` or one of its descendents. Here is a simple publisher that wraps a
sensor, and sends its values to one or more of three topics::

    class MultiTopicPublisher(Publisher, DirectPublisherMixin):
        def __init__(self, sensor):
            super().__init__(topics=['divisible_by_two', 'divisible_by_three',
                                     'other'])
            self.sensor = sensor
            
        def _observe(self):
            try:
                val = int(round(self.sensor.sample()))
                if (val%2)==0:
                    self._dispatch_next(val, topic='divisible_by_two')
                if (val%3)==0:
                    self._dispatch_next(val, topic='divisible_by_three')
                if (val%3)!=0 and (val%2)!=0:
                    self._dispatch_next(val, topic='other')                    
            except FatalError:
                raise
            except StopIteration:
                self._dispatch_completed(topic='divisible_by_two')
                self._dispatch_completed(topic='divisible_by_three')
                self._dispatch_completed(topic='other')
            except Exception as e:
                self._dispatch_error(e, topic='divisible_by_two')
                self._dispatch_error(e, topic='divisible_by_three')
                self._dispatch_error(e, topic='other')

In the ``_init__`` constructor, we must be sure to call the super class's
constructor, passing it the list of topics that will be used. If the list is
not provided, it is initialized to the default topic, and publishing to any other
topic would be a runtime error.

This is a direct publisher, so we obtain and publish sensor values in the
``_observe()`` method. We first obtain a value from the sensor and round it
to the nearest integer. Next, we see if it is divisible by 2. If so, call
``_dispatch_next()`` to dispatch the value to the ``divisible_by_two`` topic,
passing the topic name as the second parameter (it defaults to ``default``).
Next, we check for divisibity by three, and dispatch the value to the
``divisible_by_three`` topic if it is divisible. Note that a number like six
will get dispatched to both topics. Finally, if the value is not divisible by
either two or three, we dispatch it to the ``other`` topic.

Various exception conditions are also handled. Fatal errors are re-raised. If
the sensor has run out of data, we call ``_dispatch_completed()`` for each of
the three topics. If any other exception has been thrown, we call
``_dispatch_error()`` for each topic. In general, each topic can be viewed as
a separate event stream with its own state. A publisher might decide to
mark completed a subset of its topics while continuing to publish new events
on other topics.

Let us look at how this publisher might be called::

    pub = MultiTopicPublisher(sensor)
    pub.subscribe(lambda v: print("even: %s" % v),
              topic_mapping=('divisible_by_two', 'default'))
    pub.subscribe(lambda v: print("divisible by three: %s" % v),
                  topic_mapping=('divisible_by_three', 'default'))
    pub.subscribe(lambda v: print("not divisible: %s" % v),
                  topic_mapping=('other', 'default'))
    scheduler.schedule_recurring(pub)
    scheduler.run_forever()

Here, we map a different anonymous print function to each output topic of the
publisher. Internally, ``subscribe`` is wrapping the anonymous functions with
``CallableAsSubscriber``. This subscriber only listens on a default topic, so we
have to map the topic names in the ``subscribe()`` calls.

The full code for this example is at ``examples/multi_topic_publisher.py``.

Subscribing to Multiple Topics
------------------------------
Now, let us consider a subscriber that supports subscriptions to multiple
topics. Non-default subscriptions are passed to different methods on a
subscriber. Specifically, given a topic name ``TOPIC``, events are dispatched
to the method ``on_TOPIC_next()``, completion of the topic's stream is
dispatched to ``on_TOPIC_completed()``, and errors are dispatched to
``on_TOPIC_error()``. Multiple topic subscriptions are frequently useful
when implementing state machines or filters that combine multiple inputs.

As an example, assume that we have a state machine that subscribes to data
from two sensors: a *left* sensor and a *right* sensor. Here is how the code
might be structured::

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

Here is how we might set up the connections to the sensors::

    left = SensorPub(LuxSensor('left'))
    right = SensorPub(LuxSensor('right'))
    state_machine = StateMachine()
    left.subscribe(state_machine, topic_mapping=('default', 'left'))
    right.subscribe(state_machine, topic_mapping=('default', 'right'))

Each sensor outputs its data on the default topic, so we map the subscriptions
to the ``left`` and ``right`` topics on the state machine.

Multi-topic Filters
-------------------
A *filter* is an AntEvents element that is both a publisher and a subscriber.
Filters usually have a single input topic and a single output topic, but other
topologies are possible (typically one-to-many or many-to-one). One particularly
useful filter is the *dispatcher*. A dispatcher routes each incoming event
(on the default input topic) to one of several output topics, based on some
criteria.

For example, consider the filter ``antevents.linq.dispatch.Dispatcher``. This
filter is provided a set of routing rules in the form of (predicate function,
output topic) pairs. An output topic is created for each rule (plus the default
topic). In the ``on_next()`` method of the filter's subscriber interface, an
incoming event is tested on each of the predicate functions in order. When a
predicate is found that returns true, the event is dispatched to the associated
topic and the rule search stops for that event. If an event fails all the
predicate checks, it is passed to the ``default`` topic.

Here is the most relevant parts of the filter code (see ``dispatch.py`` for the
complete code)::

    class Dispatcher(Publisher, DefaultSubscriber):
        def __init__(self, previous_in_chain, dispatch_rules):
            topics = [topic for (pred, topic) in dispatch_rules] + ['default']
            super().__init__(topics=topics)
            self.dispatch_rules = dispatch_rules
            self.dispose = previous_in_chain.subscribe(self)
    
        def on_next(self, x):
            for (pred, topic) in self.dispatch_rules:
                if pred(x):
                    self._dispatch_next(x, topic=topic)
                    return
            self._dispatch_next(x, topic='default') # fallthrough case
        ...

A example application using this dispatcher along with other instances of
topic mapping may be found at ``examples_solar_heater_example.py``.


