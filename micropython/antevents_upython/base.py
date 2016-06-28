"""
Base definitions for antevents-micropython
"""

from collections import namedtuple
import time
import sys

from antevents_upython.utils import get_logger, ESP8266_PLATFORM
from antevents_upython.sensor import SensorEvent
import antevents_upython.scheduler as scheduler

class DefaultSubscriber:
    """This is the interface to be implemented by a subscriber
    which consumes the events from an publisher when subscribing
    on the default topic.
    """
    __slots__ = ()
    def on_next(self, x):
        pass
        
    def on_error(self, e):
        pass
        
    def on_completed(self):
        pass

def noop(*args, **kw):
    """No operation. Returns nothing"""
    pass

    
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
    
class Publisher:
    """Base class for event generators (publishers). The non-underscore
    methods are the public end-user interface. The methods starting with
    underscores are for interactions with the scheduler.
    """
    __slots__ = ('__subscribers__', '__topics__', '__unschedule_hook__',
                 '__closed_topics__')
    def __init__(self, topics=None):
        self.__subscribers__ = {} # map from topic to subscriber set
        if topics is None:
            self.__topics__ = set(['default',])
        else:
            self.__topics__ = set(topics)
        for topic in self.__topics__:
            self.__subscribers__[topic] = []
        self.__unschedule_hook__ = None
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
        on_next_name = _on_next_name(sub_topic)
        on_completed_name = _on_completed_name(sub_topic)
        on_error_name = _on_error_name(sub_topic)
        if not hasattr(subscriber, on_next_name) and callable(subscriber):
            # This is different from the standard python version.
            raise FatalError("Cannot pass an arbitrary callable in to subscribe, must pass something that implements subscriber interface")
        functions = []
        try:
            for m in (on_next_name, on_completed_name, on_error_name):
                functions.append(getattr(subscriber, m))
        except AttributeError:
            raise InvalidTopicError("Invalid subscribe topic '%s', no method '%s' on subscriber %s" %
                                    (sub_topic, m, subscriber))
        subscription = _Subscription(on_next=functions[0],
                                     on_completed=functions[1],
                                     on_error=functions[2], subscriber=subscriber,
                                     sub_topic=sub_topic)
        new_subscribers = self.__subscribers__[pub_topic].copy()
        new_subscribers.append(subscription)
        self.__subscribers__[pub_topic] = new_subscribers
        def dispose():
            # To remove the subsription, we replace the entire list with a copy
            # that is missing the subscription. This allows dispose() to be
            # called within a _dispatch method. Otherwise, we get an error if
            # we attempt to change the list of subscribers while iterating over
            # it.
            new_subscribers = self.__subscribers__[pub_topic].copy()
            new_subscribers.remove(subscription)
            self.__subscribers__[pub_topic] = new_subscribers
        return dispose

    def _schedule(self, unschedule_hook):
        """This method is used by the scheduler to specify a thunk to
        be called when the publisher no longer needs to be scheduled.
        Currently, this is only when the stream of events ends due to
        a completion/error events or when the user explicitly cancels
        the scheduling.
        """
        self.__unschedule_hook__ = unschedule_hook

    def _close_topic(self, topic):
        """Topic will receive no more messaeges. Remove the topic from
        this publisher.
        If all topics have been closed, we also call the unschedule hook.
        """
        #print("Closing topic %s on %s" % (topic, self)) # XXX
        del self.__subscribers__[topic]
        self.__topics__.remove(topic)
        self.__closed_topics__.append(topic)
        if len(self.__subscribers__)==0 and self.__unschedule_hook__ is not None:
            print("Calling unschedule hook for %s" % self)
            self.__unschedule_hook__()
            self.__unschedule_hook__ = None

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
        try:
            for s in subscribers:
                s.on_error(e)
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch("Unexpected exception when dispatching error '%s' to subscriber %s from publisher %s: %s" %
                                (e, s, self, e))
        self._close_topic(topic)

    def _observe(self):
        """Get an event and call the appropriate dispatch function.
        Returns True if there is more data and False otherwise.
        """
        raise NotImplemented
        
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


class StopSensor(Exception):
    """Throw this exception in the sample function to indicate you
    want to stop"""
    pass
        
class SensorPublisher(Publisher):
    """Publish values sampled from a sensor. A value is obtained
    by calling the sensor's sample() method. We wrap the value in
    a SensorEvent.
    """
    __slots__ = ('sensor', 'sensor_id')
    def __init__(self, sensor, sensor_id):
        super().__init__()
        self.sensor = sensor
        self.sensor_id = sensor_id

    def _observe(self):
        try:
            val = self.sensor.sample()
            self._dispatch_next(SensorEvent(self.sensor_id, time.time(), val))
            return True
        except FatalError:
            raise
        except StopSensor:
            self._dispatch_completed()
            return False
        except Exception as e:
            self._dispatch_error(e)
            return False

    def __repr__(self):
        return "SensorPublisher(sensor=%s, sensor_id=%s)" % \
            (self.sensor, self.sensor_id)

# We need to compute an elapsed time and return it as an integer value in
# seconds. The way to do this in micropython is different than for standard
# python.
if sys.platform==ESP8266_PLATFORM:
    def _get_start_timestamp():
        return time.ticks_ms()
    
    def _get_elapsed_time_seconds(start_timestamp):
        return int(round(time.ticks_diff(start_timestamp, time.ticks_ms())/1000))
else:
    def _get_start_timestamp():
        return time.time()
    
    def _get_elapsed_time_seconds(start_timestamp):
        return int(round(time.time() - start_timestamp))
    
    
class Scheduler:
    __slots__ = ('core')
    def __init__(self):
        self.core = scheduler.Scheduler()

    def schedule_periodic(self, publisher, interval):
        self.core.add_sensor(publisher, interval)
        def cancel():
            self.core.remove_sensor(publisher)
        return cancel

    def schedule_sensor_periodic(self, sensor, sensor_id, interval, subscribers):
        """Shorthand version for a sensor - wrap it in a publisher, connect its
        subscribers, and schedule it.
        """
        p = SensorPublisher(sensor, sensor_id)
        for s in subscribers:
            p.subscribe(s)
        return self.schedule_periodic(p, interval)

    def run_forever(self):
        get_logger().info("Entering scheduler loop")
        if self.core.is_empty():
            raise Exception("Called run_forever() when no publishers have been scheduled.")
        while True:
            publishers = self.core.get_sensors_to_sample()
            start_time = _get_start_timestamp()
            for publisher in publishers:
                more = publisher._observe()
                if not more:
                    self.core.remove_sensor(publisher)
            if self.core.is_empty():
                break
            sample_time = _get_elapsed_time_seconds(start_time)
            if sample_time > 0:
                self.core.advance_time(sample_time)
            sleeptime = self.core.get_next_sleep_interval()
            start_time = _get_start_timestamp()
            time.sleep(sleeptime)
            actual_sleep_time = _get_elapsed_time_seconds(start_time)
            self.core.advance_time(actual_sleep_time)
        get_logger().info("No more schedules active, existing scheduler loop")
