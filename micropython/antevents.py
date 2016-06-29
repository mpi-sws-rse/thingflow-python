
# antevents for micropython

from ucollections import namedtuple
import utime

class FatalError(Exception):
    pass

class ExcInDispatch(FatalError):
    # Dispatching an event should not raise an error, other than a
    # fatal error.
    pass


_Subscription = namedtuple('_Subscription',
                           ['on_next', 'on_completed', 'on_error'])


# Base class for event generators (publishers).
class Publisher:
    __slots__ = ('__subscribers__', '__unschedule_hook__')
    def __init__(self, topics=None):
        self.__subscribers__ = {} # map from topic to subscriber set
        if topics==None:
            topics = ['default']
        for topic in topics:
            self.__subscribers__[topic] = []
        self.__unschedule_hook__ = None


    def subscribe(self, subscriber, topic_mapping=None):
        if topic_mapping==None:
            pub_topic = 'default'
            sub_topic = 'default'
        else:
            (pub_topic, sub_topic) = topic_mapping
        if sub_topic==None or sub_topic=='default':
            dispatchnames = ('on_next', 'on_completed', 'on_error')
        else:
            dispatchnames = ('on_%s_next' % sub_topic,
                             'on_%s_completd' % sub_topic,
                             'on_%s_error' % sub_topic)
        functions = [getattr(subscriber, m) for m in dispatchnames]
        subscription = _Subscription(on_next=functions[0],
                                     on_completed=functions[1],
                                     on_error=functions[2])
        new_subscribers = self.__subscribers__[pub_topic].copy()
        new_subscribers.append(subscription)
        self.__subscribers__[pub_topic] = new_subscribers
        def dispose():
            new_subscribers = self.__subscribers__[pub_topic].copy()
            new_subscribers.remove(subscription)
            self.__subscribers__[pub_topic] = new_subscribers
        return dispose

    def _schedule(self, unschedule_hook):
        self.__unschedule_hook__ = unschedule_hook

    def _close_topic(self, topic):
        del self.__subscribers__[topic]
        if len(self.__subscribers__)==0 and self.__unschedule_hook__ is not None:
            print("Calling unschedule hook for %s" % self)
            self.__unschedule_hook__()
            self.__unschedule_hook__ = None

    def _dispatch_next(self, x, topic=None):
        subscribers = self.__subscribers__[topic if topic is not None
                                           else 'default']
        try:
            for s in subscribers:
                s.on_next(x)
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch(e)

    def _dispatch_completed(self, topic=None):
        subscribers = self.__subscribers__[topic if topic is not None
                                           else 'default']
        try:
            for s in subscribers:
                s.on_completed()
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch(e)
        self._close_topic(topic)

    def _dispatch_error(self, e, topic=None):
        subscribers = self.__subscribers__[topic if topic is not None
                                           else 'default']
        try:
            for s in subscribers:
                s.on_error(e)
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch(e)
        self._close_topic(topic)

    def _observe(self):
        # Get an event and call the appropriate dispatch function.
        # Return True if there is more data and False otherwise.
        raise NotImplemented


class _Interval:
    __slots__ = ('ticks', 'tasks', 'next_tick')
    def __init__(self, ticks, next_tick):
        self.ticks = ticks
        self.tasks = []
        self.next_tick = next_tick

class Scheduler:
    __slots__ = ('clock_wrap', 'time_in_ticks', 'intervals',
                 'sorted_ticks')
    def __init__(self, clock_wrap=65535):
        self.clock_wrap = clock_wrap
        self.time_in_ticks = 0
        self.intervals = {}
        self.sorted_ticks = []
        
    def _add_task(self, task, ticks):
        assert ticks > 0 and ticks < self.clock_wrap
        if ticks in self.intervals:
            self.intervals[ticks].tasks.append(task)
        else:
            next_tick = None
            for i in self.sorted_ticks:
                if (i%ticks)==0 or (ticks%i)==0:
                    next_tick = self.intervals[i].next_tick
                    break
            if next_tick is None:
                next_tick = self.time_in_ticks # otherwise use now
            interval = _Interval(ticks, next_tick)
            interval.tasks.append(task)
            self.intervals[ticks] = interval
            self.sorted_ticks.append(ticks)
            self.sorted_ticks.sort()

    def _remove_task(self, task):
        for interval in self.intervals.values():
            if task in interval.tasks:
                interval.tasks.remove(task)
                if len(interval.tasks)==0:
                    self.sorted_ticks.remove(interval.ticks)
                    del self.intervals[interval.ticks]
                return
        assert 0, "Did not find task %s" % task

    def _get_next_sleep_interval(self):
        assert len(self.intervals)>0
        sleep_time = self.clock_wrap
        for interval in self.intervals.values():
            time_diff = max(interval.next_tick-self.time_in_ticks, 0)
            if time_diff < sleep_time:
                sleep_time = time_diff
        return sleep_time

    def _advance_time(self, ticks):
        assert ticks < self.clock_wrap
        self.time_in_ticks += ticks
        if self.time_in_ticks >= self.clock_wrap:
            # wrap all the clocks
            unwrapped_time = self.time_in_ticks
            self.time_in_ticks = self.time_in_ticks % self.clock_wrap
            for interval in self.intervals.values():
                if interval.next_tick >= self.clock_wrap:
                    interval.next_tick = interval.next_tick % self.clock_wrap
                else: # the interval is already overdue
                    interval.next_tick = self.time_in_ticks - \
                                         (unwrapped_time-interval.next_tick)
                    
    def _get_tasks_to_sample(self):
        sample_list = []
        for ticks in self.sorted_ticks:
            interval = self.intervals[ticks]
            if interval.next_tick<=self.time_in_ticks:
                sample_list.extend(interval.tasks)
                interval.next_tick = interval.next_tick + interval.ticks
        return sample_list

    def schedule_periodic(self, publisher, interval):
        self._add_task(publisher, interval)
        def cancel():
            self._remove_task(publisher)
        return cancel

    def run_forever(self):
        if len(self.intervals)==0:
            raise FatalError("No publishers have been scheduled.")
        while True:
            publishers = self._get_tasks_to_sample()
            start_ts = utime.ticks_ms()
            for publisher in publishers:
                more = publisher._observe()
                if not more:
                    self._remove_task(publisher)
            if len(self.intervals)==0:
                break
            end_ts = utime.ticks_ms()
            sample_time = int(round(utime.ticks_diff(start_ts, end_ts)/1000))
            if sample_time > 0:
                self._advance_time(sample_time)
            sleeptime = self._get_next_sleep_interval()
            utime.sleep(sleeptime)
            wake_ts = utime.ticks_ms()
            actual_sleep_time = int(round(utime.ticks_diff(end_ts,
                                                           wake_ts)/1000))
            self._advance_time(actual_sleep_time)


SensorEvent = namedtuple('SensorEvent', ['sensor_id', 'ts', 'val'])
