# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
Base functionality for ant events. All the core abstractions
are defined here. Everything else is just subclassing or using
these abstractions.

The key abstractions are:

 * Publisher   - a publisher is a data source that puts out a stream of events
                 for each topic it defines.
 * Sensor      - an object that is (indirectly) connected to the physical world.
                 It can provide its current value through a sample() method.
                 Sensors can be turned into publishers by wrapping them with
                 the SensorPub class.
 * Subscriber  - a data sink that receives a stream of events for each topic it
                 defines.
 * Filter      - a component that is both a publisher and a subscriber. Filters
                 transform data streams.
 * Scheduler   - The scheduler wraps an event loop. It provides periodic and
                 one-time scheduling of publishers that originate events.
 * event       - antevents largely does not care about the particulars of the
                 events it processes. However, we define a generic SensorEvent
                 datatype that can be used when the details of the event matter
                 to a component.

See the README.rst file for more details.
"""

import types
from collections import namedtuple
import threading
import time
import queue
import logging
logger = logging.getLogger(__name__)

from antevents.internal import noop


class DefaultSubscriber:
    """This is the interface to be implemented by a subscriber
    which consumes the events from an publisher when subscribing
    on the default topic.
    """
    def on_next(self, x):
        pass
        
    def on_error(self, e):
        pass
        
    def on_completed(self):
        pass


def _on_next_name(topic):
    if topic==None or topic=='default':
        return 'on_next'
    else:
        return 'on_%s_next' % topic

def _on_error_name(topic):
    if topic==None or topic=='default':
        return 'on_error'
    else:
        return 'on_%s_error' % topic


def _on_completed_name(topic):
    if topic==None or topic=='default':
        return 'on_completed'
    else:
        return 'on_%s_completed' % topic


class CallableAsSubscriber:
    """Wrap any callable with the Subscriber interface.
    We only pass it the on_next() calls. on_error and on_completed
    can be passed in or default to noops.
    """
    def __init__(self, on_next=None, on_error=None, on_completed=None,
                 topic=None):
        setattr(self, _on_next_name(topic), on_next or noop)
        if on_error:
            setattr(self, _on_error_name(topic), on_error)
        else:
            def default_error(err):
                if isinstance(err, FatalError):
                    raise err
                else:
                    logger.error("%s: Received on_error(%s)" %
                                 (self, err))
            setattr(self, _on_error_name(topic), default_error)
        setattr(self, _on_completed_name(topic), on_completed or noop)
        
    def __str__(self):
        return 'CallableAsSubscriber(%s)' % self.on_next.__str__()


class FatalError(Exception):
    """This is the base class for exceptions that should terminate the event
    loop. This should be for out-of-bound errors, not for normal errors in
    the data stream. Examples of out-of-bound errors include an exception
    in the infrastructure or an error in configuring or dispatching an event
    stream (e.g. publishing to a non-existant topic).
    """
    pass

class InvalidTopicError(FatalError):
    pass

class UnknownTopicError(FatalError):
    pass

class TopicAlreadyClosed(FatalError):
    pass


class ExcInDispatch(FatalError):
    """Dispatching an event should not raise an error, other than a
    fatal error.
    """
    pass

# Internal representation of a subscription. The first three fields
# are functions which dispatch to the subscriber. The subscriber and sub_topic
# fields are not needed at runtime, but helpful in debugging.
_Subscription = namedtuple('_Subscription',
                           ['on_next', 'on_completed', 'on_error', 'subscriber',
                            'sub_topic'])
    
class Publisher:
    """Base class for event generators (publishers). The non-underscore
    methods are the public end-user interface. The methods starting with
    underscores are for interactions with the scheduler.
    """
    def __init__(self, topics=None):
        self.__subscribers__ = {} # map from topic to subscriber set
        if topics is None:
            self.__topics__ = set(['default',])
        else:
            self.__topics__ = set(topics)
        for topic in self.__topics__:
            self.__subscribers__[topic] = []
        self.__enqueue_fn__ = None
        self.__closed_topics__ = []


    def subscribe(self, subscriber, topic_mapping=None):
        """Subscribe the subscriber to events on a specific topic. The topic
        mapping is a tuple of the publisher's topic name and subscriber's topic
        name. It defaults to (default, default).
        """
        if topic_mapping==None:
            pub_topic = 'default'
            sub_topic = 'default'
        else:
            (pub_topic, sub_topic) = topic_mapping
        if pub_topic not in self.__topics__:
            raise InvalidTopicError("Invalid publish topic '%s', valid topics are %s" %
                                    (pub_topic,
                                     ', '.join([str(s) for s in self.__topics__])))
        if not hasattr(subscriber, _on_next_name(sub_topic)) and callable(subscriber):
                subscriber = CallableAsSubscriber(subscriber, topic=sub_topic)
        try:
            subscription = \
                _Subscription(on_next=getattr(subscriber, _on_next_name(sub_topic)),
                              on_completed=getattr(subscriber, _on_completed_name(sub_topic)),
                              on_error=getattr(subscriber, _on_error_name(sub_topic)),
                              subscriber=subscriber,
                              sub_topic=sub_topic)
        except AttributeError:
            raise InvalidTopicError("Invalid subscribe topic '%s', missing method(s) on subscriber %s" %
                                    (sub_topic, subscriber))
        new_subscribers = self.__subscribers__[pub_topic].copy()
        new_subscribers.append(subscription)
        self.__subscribers__[pub_topic] = new_subscribers
        def dispose():
            # To remove the subscription, we replace the entire list with a copy
            # that is missing the subscription. This allows dispose() to be
            # called within a _dispatch method. Otherwise, we get an error if
            # we attempt to change the list of subscribers while iterating over
            # it.
            new_subscribers = self.__subscribers__[pub_topic].copy()
            new_subscribers.remove(subscription)
            self.__subscribers__[pub_topic] = new_subscribers
        return dispose

    def _schedule(self, enqueue_fn):
        """This method is used by the scheduler to specify an enqueue function
        to be called
        when dispatching events to the subscribers. This is used when the
        publisher runs in a separate thread from the main event loop. If
        that is not the case, the enqueue function should be None.
        """
        self.__enqueue_fn__ = enqueue_fn

    def _close_topic(self, topic):
        """Topic will receive no more messaeges. Remove the topic from
        this publisher.
        If all topics have been closed, we also call the unschedule hook.
        """
        #print("Closing topic %s on %s" % (topic, self)) # XXX
        del self.__subscribers__[topic]
        self.__topics__.remove(topic)
        self.__closed_topics__.append(topic)

    def _dispatch_next(self, x, topic=None):
        #print("Dispatch next called on %s, topic %s, msg %s" % (self, topic, str(x)))
        if topic==None:
            topic = 'default'
        try:
            subscribers = self.__subscribers__[topic]
        except KeyError:
            if topic in self.__closed_topics__:
                raise TopicAlreadyClosed("Topic '%s' on publisher %s already had an on_completed or on_error_event" %
                                         (topic, self))
            else:
                raise UnknownTopicError("Unknown topic '%s' in publisher %s" %
                                        (topic, self))
        if len(subscribers) == 0:
            return
        enq = self.__enqueue_fn__
        if enq:
            for s in subscribers:
                enq(s.on_next, x)
        else:
            try:
                for s in subscribers:
                    s.on_next(x)
            except FatalError:
                raise
            except Exception as e:
                raise ExcInDispatch("Unexpected exception when dispatching event '%s' to subscriber %s from publisher %s: %s" %
                                    (x, s, self, e))

    def _dispatch_completed(self, topic=None):
        if topic==None:
            topic = 'default'
        try:
            subscribers = self.__subscribers__[topic]
        except KeyError:
            if topic in self.__closed_topics__:
                raise TopicAlreadyClosed("Topic '%s' on publisher %s already had an on_completed or on_error_event" %
                                         (topic, self))
            else:
                raise UnknownTopicError("Unknown topic '%s' in publisher %s" % (topic, self))
        enq = self.__enqueue_fn__
        if enq:
            for s in subscribers:
                enq(s.on_completed)
        else:
            try:
                for s in subscribers:
                    s.on_completed()
            except FatalError:
                raise
            except Exception as e:
                raise ExcInDispatch("Unexpected exception when dispatching completed to subscriber %s from publisher %s: %s" %
                                    (s, self, e))
        self._close_topic(topic)

    def _dispatch_error(self, e, topic=None):
        if topic==None:
            topic = 'default'
        try:
            subscribers = self.__subscribers__[topic]
        except KeyError:
            if topic in self.__closed_topics__:
                raise TopicAlreadyClosed("Topic '%s' on publisher %s already had an on_completed or on_error_event" %
                                         (topic, self))
            else:
                raise UnknownTopicError("Unknown topic '%s' in publisher %s" % (topic, self))
        enq = self.__enqueue_fn__
        if enq:
            for s in subscribers:
                enq(s.on_error, e)
        else:
            try:
                for s in subscribers:
                    s.on_error(e)
            except FatalError:
                raise
            except Exception as e:
                raise ExcInDispatch("Unexpected exception when dispatching error '%s' to subscriber %s from publisher %s: %s" %
                                    (e, s, self, e))
        self._close_topic(topic)

    def print_downstream(self):
        """Recursively print all the downstream paths. This is for debugging.
        """
        def has_subscribers(step):
            if not hasattr(step, '__subscribers__'):
                return False
            for topic in step.__subscribers__.keys():
                if len(step.__subscribers__[topic])>0:
                    return True
            return False
        def print_from(current_seq, step):
            if has_subscribers(step):
                for (topic, subscribers) in step.__subscribers__.items():
                    for subscription in subscribers:
                        if topic=='default' and \
                           subscription.sub_topic=='default':
                            next_seq = " => %s" % subscription.subscriber
                        else:
                            next_seq = " [%s]=>[%s] %s" % \
                                        (topic, subscription.sub_topic,
                                         subscription.subscriber)
                        print_from(current_seq + next_seq,
                                   subscription.subscriber)
            else:
                print(current_seq)
        print("***** Dump of all paths from %s *****" % self.__str__())
        print_from("  " + self.__str__(), self)
        print("*"*(12+len(self.__str__())))

    def pp_subscribers(self):
        """pretty print the set of subscribers"""
        h1 = "***** Subscribers for %s *****" % self
        print(h1)
        for topic in sorted(self.__subscribers__.keys()):
            print("  Topic %s" % topic)
            for s in self.__subscribers__[topic]:
                print("    [%s] => %s" % (s.sub_topic, s.subscriber))
                print("      on_next: %s" % s.on_next)
                print("      on_completed: %s" % s.on_completed)
                print("      on_error: %s" % s.on_error)
        print("*"*len(h1))
        
                
    
class Filter(Publisher, DefaultSubscriber):
    def __init__(self, previous_in_chain,
                 on_next=None, on_completed=None,
                 on_error=None, name=None):
        super().__init__()
        self._on_next = on_next
        self._on_completed = on_completed
        self._on_error = on_error
        self.name = name
        self.dispose = previous_in_chain.subscribe(self) # XXX how to use this?

    def on_next(self, x):
        if self._on_next:
            try:
                self._on_next(self, x)
            except FatalError:
                raise
            except Exception as e:
                logger.exception("Got an exception on %s.on_next(%s)" %
                                 (self, x))
                self.on_error(e)
                self.dispose() # stop from getting upstream events
        else:
            self._dispatch_next(x)
        
    def on_error(self, e):
        if self._on_error:
            self._on_error(self, e)
        else:
            self._dispatch_error(e)
        
    def on_completed(self):
        if self._on_completed:
            self._on_completed(self)
        else:
            self._dispatch_completed()

    def __str__(self):
        if hasattr(self, 'name') and self.name:
            return self.name
        else:
            return super().__str__()


def _is_thunk(t):
    return hasattr(t, '__thunk__')

def _make_thunk(t):
    setattr(t, '__thunk__', True)

class _ThunkBuilder:
    """This is used to create a thunk from a linq-style
    method.
    """
    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__

    def __call__(self, *args, **kwargs):
        if len(args)==0 and len(kwargs)==0:
            _make_thunk(self.func)
            return self.func
        def apply(this):
            return self.func(this, *args, **kwargs)
        apply.__name__ = self.__name__
        _make_thunk(apply)
        return apply
    def __repr__(self):
        return "_ThunkBuilder(%s)" % self.__name__

def _subscribe_thunk(prev, thunk):
    """Subscribe the thunk to the previous in the chain. Handles
    all the cases where we might be given a filter, a thunk,
    a thunk builder (unevaluated linq function), or a bare callable."""
    if callable(thunk):
        if _is_thunk(thunk):
            return thunk(prev)
        elif isinstance(thunk, _ThunkBuilder):
            real_thunk = thunk()
            assert _is_thunk(real_thunk)
            return real_thunk(prev)
        else: # bare callable, will be wrapped by the subscribe method
            prev.subscribe(thunk)
            return None
    else:
        return prev.subscribe(thunk) # assumed to be a filter
    

def filtermethod(base, alias=None):
    """Function decorator that creates a linq-style filter out of the
    specified function. As described in the antevents.linq documentation,
    it should take a Publisher as its first argument (the source of events)
    and return a Publisher (representing the end the filter sequence once
    the filter is included. The returned Publisher is typically an instance
    of antevents.base.Filter.

    The specified function is used in two places:
    1. A method with the specified name is added to the specified class
       (usually the Publisher base class). This is for the fluent (method
       chaining) API.
    2. A function is created in the local namespace for use in the functional API.
       This function does not take the publisher as an argument. Instead,
       it takes the remaining arguments and then returns a function which,
       when passed a publisher, subscribes to it and returns a filter.

    Decorator arguments:
    :param T base: Base class to extend with method
     (usually antevents.base.Publisher)
    :param string alias: an alias for this function or list of aliases
                         (e.g. map for select, etc.).

    :returns: A function that takes the class to be decorated.
    :rtype: func -> func

    This was adapted from the RxPy extensionmethod decorator.
    """
    def inner(func):
        """This function is returned by the outer filtermethod()

        :param types.FunctionType func: Function to be decorated
        """

        func_names = [func.__name__,]
        if alias:
            aliases = alias if isinstance(alias, list) else [alias]
            func_names += aliases

        _thunk = _ThunkBuilder(func)

        # For the primary name and all aliases, set the name on the
        # base class as well as in the local namespace.
        for func_name in func_names:
            setattr(base, func_name, func)
            func.__globals__[func_name] = _thunk
        return _thunk
    return inner


class DirectPublisherMixin:
    """This is the interface for publishers that should be directly
    scheduled by the scheduler (e.g. through schedule_recurring(),
    schedule_periodic(), or schedule_periodic_on_separate_thread).
    """
    def _observe(self):
        """Get an event and call the appropriate dispatch function.
        """
        raise NotImplemented
    

class EventLoopPublisherMixin:
    """Publisher that gets messages from an event loop, either the same
    loop as the scheduler or a separate one.
    """
    def _observe_event_loop(self):
        """Call the event publisher's event loop. When
        an event occurs, the appropriate _dispatch method should
        be called.
        """
        raise NotImplemented

    def _stop_loop(self):
        """When this method is called, the publisher should exit the
        event loop as soon as possible.
        """
        raise NotImplemented


class IterableAsPublisher(Publisher, DirectPublisherMixin):
    """Convert any interable to an Publisher. This can be
    used with the schedule_recurring() and schedule_periodic()
    methods of the scheduler.
    """
    def __init__(self, iterable, name=None):
        super().__init__()
        self.iterable = iterable
        self.name = name
    
    def _observe(self):
        try:
            event = self.iterable.__next__()
            self._dispatch_next(event)
        except StopIteration:
            self._close()
            self._dispatch_completed()
        except FatalError:
            self._close()
            raise
        except Exception as e:
            self._close()
            self._dispatch_error(e)

    def _close(self):
        """This method is called when we stop the iteration, either due to
        reaching the end of the sequence or an error. It can be overridden by
        subclasses to clean up any state and release resources (e.g. closing
        open files/connections).
        """
        pass
    
    def __str__(self):
        if hasattr(self, 'name') and self.name:
            return self.name
           
def from_iterable(i):
    return IterableAsPublisher(i)

def from_list(l):
    return IterableAsPublisher(iter(l))

class FunctionIteratorAsPublisher(Publisher, DirectPublisherMixin):
    """Generates an publisher sequence by running a state-driven loop
        producing the sequence's elements
        Example:
        res = GeneratePublisher(0,
                                 lambda x: x < 10,
                                 lambda x: x + 1,
                                 lambda x: x)

        initial_state: Initial state.
        condition: Condition to terminate generation (upon returning False).
        iterate: Iteration step function.
        result_selector: Selector function for results produced in the sequence.

        Returns the generated sequence.
    """

    def __init__(self, initial_state, condition, iterate, result_selector):
        super().__init__()
        self.value = initial_state
        self.condition = condition
        self.iterate = iterate
        self.result_selector = result_selector 
        self.first = True

    def _observe(self):
        try:
            if self.first: # first time: just send the value
                self.first = False
                if self.condition(self.value):
                    r = self.result_selector(self.value)
                    self._dispatch_next(r)
                else:
                    self._dispatch_completed()
            else:
                if self.condition(self.value):
                    self.value = self.iterate(self.value)
                    r = self.result_selector(self.value)
                    self._dispatch_next(r)
                else: 
                    self._dispatch_completed()
        except Exception as e:
            self._dispatch_error(e)

def from_func(init, cond, iter, selector):
    return FunctionIteratorAsPublisher(init, cond, iter, selector)

    def __str__(self):
        if hasattr(self, 'name') and self.name:
            return self.name
        else:
            super().__str__()


# Define a default sensor event as a tuple of sensor id, timestamp, and value.
SensorEvent = namedtuple('SensorEvent', ['sensor_id', 'ts', 'val'])

def make_sensor_event(sensor, sample):
    """Given a sensor object and a sample taken from that sensor,
    return a SensorEvent tuple."""
    return SensorEvent(sensor_id=sensor.sensor_id, ts=time.time(),
                       val=sample)


class SensorPub(Publisher, DirectPublisherMixin):
    """Publisher that samples a sensor upon its observe call, creates
    an event from the sample, and dispatches it forward. A sensor is just
    an object that has a sensor_id property and a sample() method. If the
    sensor wants to complete the stream, it should throw a StopIteration
    exception.

    By default, it generates SensorEvent instances. This behavior can be
    changed by passing in a different function for make_event_fn.
    """
    def __init__(self, sensor, make_event_fn=make_sensor_event):
        super().__init__()
        self.sensor = sensor
        self.make_event_fn = make_event_fn
        
    def _observe(self):
        try:
            self._dispatch_next(self.make_event_fn(self.sensor,
                                                   self.sensor.sample()))
        except FatalError:
            raise
        except StopIteration:
            self._dispatch_completed()
        except Exception as e:
            self._dispatch_error(e)
    
    def __repr__(self):
        return 'SensorPub(%s)' % repr(self.sensor)


class BlockingSubscriber:
    """This implements a subscriber which may potential block when sending an
    event outside the system. The subscriber is run on a separate thread. We
    create proxy methods for each topic that can be called directly - these
    methods just queue up the call to run in the worker thread. 

    The actual implementation of the subscriber goes in the _on_next,
    _on_completed, and _on_error methods. Note that we don't dispatch to separate
    methods for each topic. This is because the topic is likely to end up as
    just a message field rather than as a separate destination in the lower
    layers.
    """
    def __init__(self, scheduler, topics=None):
        if topics==None:
            self.topics = ['default',]
        else:
            self.topics = topics
        self.num_closed_topics = 0
        # create local proxy methods for each topic
        for topic in self.topics:
            setattr(self, _on_next_name(topic),
                    lambda x: self.__queue__.put((self._on_next, False,
                                                     [topic, x]),))
            setattr(self, _on_completed_name(topic),
                    lambda: self.__queue__.put((self._on_completed, True,
                                                [topic]),))
            setattr(self, _on_error_name(topic),
                    lambda e: self.__queue__.put((self._on_error, True,
                                                  [topic, e]),))
        self.__queue__ = queue.Queue()
        self.scheduler = scheduler
        self.thread = _ThreadForBlockingSubscriber(self, scheduler)
        self.scheduler.active_schedules[self] = self.request_stop
        def start():
            self.thread.start()
        self.scheduler.event_loop.call_soon(start)

    def request_stop(self):
        """This can be called to stop the thread before it is automatically
        stopped when all topics are closed. The close() method will be
        called and the subscriber cannot be restarted later.
        """
        if self.thread==None:
            return # no thread to stop
        self.__queue__.put(None) # special stop token

    def _wait_and_dispatch(self):
        """Called by main loop of blocking thread to block for a request
        and then dispatch it. Returns True if it processed a normal request
        and False if it got a stop message or there is no more events possible.
        """
        action = self.__queue__.get()
        if action is not None:
            (method, closing_topic, args) = action
            method(*args)
            if closing_topic:
                self.num_closed_topics += 1
                if self.num_closed_topics==len(self.topics):
                    # no more topics can receive events, treat this
                    # as a stop.
                    print("Stopping blocking subscriber %s" % self)
                    return False
            return True # more work possible
        else:
            return False # stop requested
        
        
    def _on_next(self, topic, x):
        """Process the on_next event. Called in blocking thread."""
        pass

    def _on_completed(self, topic):
        """Process the on_completed event. Called in blocking thread."""
        pass

    def _on_error(self, topic, e):
        """Process the on_error event. Called in blocking thread."""
        pass

    def _close(self):
        """This is called when all topics have been closed. This can be used
        to close any connections, etc.
        """
        pass

    
class _ThreadForBlockingSubscriber(threading.Thread):
    """Background thread for a subscriber that passes events to the
    external world and might block.
    """
    def __init__(self, subscriber, scheduler):
        self.subscriber = subscriber
        self.scheduler= scheduler
        self.stop_requested = False
        super().__init__()

    def run(self):
        try:
            more = True
            while more:
                more = self.subscriber._wait_and_dispatch()                
        except Exception as e:
            msg = "_wait_and_dispatch for %s exited with error: %s" % \
                  (self.subscriber, e)
            logger.exception(msg)
            self.subscriber._close()
            self.subscriber.thread = None # disassociate this thread
            def die(): # need to stop the scheduler in the main loop
                del self.scheduler.active_schedules[self.subscriber]
                raise ScheduleError(msg)
            self.scheduler.event_loop.call_soon_threadsafe(die)
        else:
            self.subscriber._close()
            self.subscriber.thread = None # disassociate this thread
            def done():
                self.scheduler._remove_from_active_schedules(self.subscriber)
            self.scheduler.event_loop.call_soon_threadsafe(done)
                


class _ThreadForBlockingPublisher(threading.Thread):
    """Background thread for publishers that might block.
    """
    def __init__(self, publisher, interval, scheduler):
        self.publisher = publisher
        self.interval = interval
        self.scheduler = scheduler
        self.stop_requested = False
        super().__init__()

    def _stop_loop(self):
        self.stop_requested = True

    def run(self):
        def enqueue_fn(fn, *args):
            self.scheduler.event_loop.call_soon_threadsafe(fn, *args)
        self.publisher._schedule(enqueue_fn=enqueue_fn)
            
        try:
            while True:
                if self.stop_requested:
                    break
                start = time.time()
                self.publisher._observe()
                if len(self.publisher.__subscribers__)==0:
                    break
                time_left = self.interval - (time.time() - start)
                if time_left > 0 and (not self.stop_requested):
                    time.sleep(time_left)
        except Exception as e:
            msg = "_observe for %s exited with error: %s" % \
                  (self.publisher, e)
            logger.exception(msg)
            def die(): # need to stop the scheduler in the main loop
                del self.scheduler.active_schedules[self.publisher]
                raise ScheduleError(msg)
            self.scheduler.event_loop.call_soon_threadsafe(die)
        else:
            def done():
                self.scheduler._remove_from_active_schedules(self.publisher)
            self.scheduler.event_loop.call_soon_threadsafe(done)
            
            
class ScheduleError(FatalError):
    pass


class Scheduler:
    """Wrap an asyncio event loop and provide methods for various kinds of
    periodic scheduling.
    """
    def __init__(self, event_loop):
        self.event_loop = event_loop
        self.active_schedules = {} # mapping from task to schedule handle
        self.pending_futures = {}
        self.next_future_id = 1
        # Set the following to an exception if we are exiting the loop due to
        # an exception. We will then raise a SchedulerError when the event loop
        # exits.
        self.fatal_error = None
        # we set the exception handler to stop all active schedules and
        # break out of the event loop if we get an unexpected error.
        def exception_handler(loop, context):
            assert loop==self.event_loop
            loop.default_exception_handler(context)
            self.fatal_error = context['message']
            self.stop()
        self.event_loop.set_exception_handler(exception_handler)

    def _remove_from_active_schedules(self, publisher):
        """Remove the specified publisher from the active_schedules map.
        If there are no more active schedules, we will request exiting of
        the event loop. This method must be run from the main thread.
        """
        del self.active_schedules[publisher]
        if len(self.active_schedules)==0:
            print("No more active schedules, will exit event loop")
            self.stop()

    def schedule_periodic(self, publisher, interval):
        """Returns a callable that can be used to remove the publisher from the
        scheduler.
        """
        def cancel():
            try:
                handle = self.active_schedules[publisher]
            except KeyError:
                raise ScheduleError("Attempt to de-schedule publisher %s, which does not have an active schedule" %
                                    publisher)
            handle.cancel()
            self._remove_from_active_schedules(publisher)
        def run():
            assert publisher in self.active_schedules
            publisher._observe()
            more = len(publisher.__subscribers__)>0
            if not more and publisher in self.active_schedules:
                self._remove_from_active_schedules(publisher)
            elif publisher in self.active_schedules:
                handle = self.event_loop.call_later(interval, run)
                self.active_schedules[publisher] = handle
                publisher._schedule(enqueue_fn=None)
        handle = self.event_loop.call_later(interval, run)
        self.active_schedules[publisher] = handle
        publisher._schedule(enqueue_fn=None)
        return cancel

    def schedule_sensor(self, sensor, interval, *subscriber_sequence,
                        make_event_fn=make_sensor_event,
                        print_downstream=False):
        """Create a publisher wrapper for the sensor and schedule it at the
        specified interval. Compose the specified subscribers (and/or thunks)
        into a sequence and subscribe the sequence to the sensor's publisher.
        Returns a thunk that can be used to remove the publisher from the
        scheduler.
        """
        publisher = SensorPub(sensor, make_event_fn=make_event_fn)
        prev = publisher
        for s in subscriber_sequence:
            assert prev,\
                "attempted to compose a terminal subscriber/thunk in a non-final position"
            prev = _subscribe_thunk(prev, s)
        if print_downstream:
            publisher.print_downstream() # just for debugging
        return self.schedule_periodic(publisher, interval)
    
    def schedule_recurring(self, publisher):
        """Takes a DirectPublisherMixin and calls _observe() to get events. If
        _observe() returns True, the task is requeued on the event queue. This
        variant is useful for something like an iterable. If the call to get
        the next event would block, don't use this! Instead, one of the calls
        that runs in a separate thread (e.g. schedule_recuring_separate_thread()
        or schedule_periodic_separate_thread()).

        Returns a callable that can be used to remove the publisher from the
        scheduler.
        """
        def cancel():
            print("canceling schedule of %s" % publisher)
            try:
                handle = self.active_schedules[publisher]
            except KeyError:
                raise ScheduleError("Attempt to de-schedule publisher %s, which does not have an active schedule" %
                                    publisher)
            handle.cancel()
            self._remove_from_active_schedules(publisher)
        def run():
            assert publisher in self.active_schedules
            publisher._observe()
            more = len(publisher.__subscribers__)>0
            if not more and publisher in self.active_schedules:
                self._remove_from_active_schedules(publisher)
            elif publisher in self.active_schedules:
                handle = self.event_loop.call_soon(run)
                self.active_schedules[publisher] = handle
                publisher._schedule(enqueue_fn=None)
        handle = self.event_loop.call_soon(run)
        self.active_schedules[publisher] = handle
        publisher._schedule(enqueue_fn=None)
        return cancel

    def schedule_on_main_event_loop(self, publisher):
        """Schedule an publisher that runs on the main event loop.
        The publisher is assumed to implement EventLoopPublisherMixin.
        Returns a callable that can be used to unschedule the publisher.
        """
        def stop():
            # tell the publisher to stop. When the publisher has finished
            # processing any messages, it MUST call
            # _remove_from_active_schedules() on the scheduler.
            publisher._stop_loop()
        self.active_schedules[publisher] = stop
        self.event_loop.call_soon(publisher._observe_event_loop)
        return stop
    
    def schedule_on_private_event_loop(self, publisher):
        """Schedule an publisher that has its own event loop on another thread.
        The publisher is assumed to implement EventLoopPublisherMixin.
        Returns a callable that can be used to unschedule the publisher, by
        requesting that the event loop stop.
        """
        def enqueue_fn(fn, *args):
            self.event_loop.call_soon_threadsafe(fn, *args)
        def thread_main():
            try:
                publisher._schedule(enqueue_fn=enqueue_fn)
                # ok, lets run the event loop
                publisher._observe_event_loop()
            except Exception as e:
                msg = "Event loop for %s exited with error: %s" % \
                                 (publisher, e)
                logger.exception(msg)
                def die(): # need to stop the scheduler in the main loop
                    del self.active_schedules[publisher]
                    raise ScheduleError(msg)
                self.event_loop.call_soon_threadsafe(die)
            else:
                def loop_done():
                    self._remove_from_active_schedules(publisher)
                self.event_loop.call_soon_threadsafe(loop_done)
                    
        t = threading.Thread(target=thread_main)
        self.active_schedules[publisher] = publisher._stop_loop
        self.event_loop.call_soon(t.start)
        return publisher._stop_loop

    def schedule_periodic_on_separate_thread(self, publisher, interval):
        """Schedule an publisher to run in a separate thread. It should
        implement the DirectPublisherMixin.
        Returns a callable that can be used to unschedule the publisher, by
        requesting that the child thread stop.
        """
        t = _ThreadForBlockingPublisher(publisher, interval, self)
        self.active_schedules[publisher] = t._stop_loop
        self.event_loop.call_soon(t.start)
        return t._stop_loop

    def schedule_sensor_on_separate_thread(self, sensor, interval, *subscriber_sequence,
                                           make_event_fn=make_sensor_event):
        """Create a publisher wrapper for the sensor and schedule it at the
        specified interval. Compose the specified subscribers (and/or thunks)
        into a sequence and subscribe the sequence to the sensor's publisher.
        Returns a thunk that can be used to remove the publisher from the
        scheduler.
        """
        publisher = SensorPub(sensor, make_event_fn=make_event_fn)
        prev = publisher
        for s in subscriber_sequence:
            assert prev,\
                "attempted to compose a terminal subscriber/thunk in a non-final position"
            prev = _subscribe_thunk(prev, s)
        return self.schedule_periodic_on_separate_thread(publisher, interval)
    
    def schedule_later_one_time(self, publisher, interval):
        def cancel():
            print("canceling schedule of %s" % publisher)
            try:
                handle = self.active_schedules[publisher]
            except KeyError:
                raise ScheduleError("Attempt to de-schedule publisher %s, which does not have an active schedule" %
                                    publisher)
            handle.cancel()
            self._remove_from_active_schedules(publisher)
        def run():
            assert publisher in self.active_schedules
            # Remove from the active schedules since this was a one-time schedule.
            # Note that the _observe() call could potentially reschedule the
            # publisher through another call to the scheduler.
            self._remove_from_active_schedules(publisher)
            publisher._observe()
        handle = self.event_loop.call_later(interval, run)
        self.active_schedules[publisher] = handle
        publisher._schedule(enqueue_fn=None)
        return cancel
    
    def run_forever(self):
        """Call the event loop's run_forever(). We don't really run forever:
        the event loop is exited if we run out of scheduled events or if stop()
        is called.
        """
        try:
            self.event_loop.run_forever()
        except KeyboardInterrupt:
            # If someone hit Control-C to break out of the loop,
            # they might be trying to diagonose a hang. Print the
            # active publishers here before passing on the interrupt.
            print("Active publishers: %s" %
                  ', '.join([('%s'%o) for o in self.active_schedules.keys()]))
            raise
        if self.fatal_error is not None:
            raise ScheduleError("Scheduler aborted due to fatal error: %s" %
                                self.fatal_error)

    def _schedule_coroutine(self, coro, done_callback):
        """This is for low-level components that deal directly with
        the event loop to to schedule a coroutine. We
        track them so we can either wait for or cancel them when stop()
        is called.
        """
        fid = self.next_future_id
        future = self.event_loop.create_task(coro)
        # the combined callback. To avoid race conditions, always
        # call the provided done callback before we remove the future.
        def cb(f):
            done_callback(f)
            del self.pending_futures[fid]
        self.pending_futures[fid] = future
        future.add_done_callback(cb)
        self.next_future_id += 1
        return future
        
    def stop(self):
        """Stop any active schedules for publishers and then call stop() on
        the event loop.
        """
        for (task, handle) in self.active_schedules.items():
            print("Stopping %s" % task)
            # The handles are either event scheduler handles (with a cancel
            # method) or just callables to be called directly.
            if hasattr(handle, 'cancel'):
                handle.cancel()
            else:
                handle()
        self.active_schedules = {}
        # go through the pending futures. We don't stop the
        # event loop until all the pending futures have been
        # completed or stopped by their callers.
        for (fid, f) in self.pending_futures.items():
            if f.done() == False:
                # if we still have pending futures, we try the
                # stop again after the first one we see has
                # completed.
                #print("Waiting for future %d (%s)" % (fid, repr(f)))
                def recheck_stop(f):
                    exc = f.exception()
                    if exc:
                        raise FatalError("Exception in coroutine %s: %s" %
                                         (repr(f), exc))
                    else:
                        self.stop()
                f.add_done_callback(recheck_stop)
                return
            elif f.exception():
                raise FatalError("Exception in coroutine %s: %s" %
                                 (repr(f), f.exception()))
        self.event_loop.stop()
