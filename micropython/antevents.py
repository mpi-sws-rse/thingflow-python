
# antevents for micropython

from ucollections import namedtuple
import utime

class FatalError(Exception):
    pass

class ExcInDispatch(FatalError):
    # Dispatching an event should not raise an error, other than a fatal error.
    pass


_Subscription = namedtuple('_Subscription', ['on_next', 'on_completed', 'on_error'])

# Base class for event generators (publishers).
class Publisher:
    __slots__ = ('__subscribers__',)
    def __init__(self, topics=None):
        self.__subscribers__ = {}
        if topics==None:
            topics = ['default']
        for topic in topics:
            self.__subscribers__[topic] = []

    def subscribe(self, subscriber, topic_map=None):
        if topic_map==None:
            pub_topic = 'default'
            sub_topic = 'default'
        else:
            (pub_topic, sub_topic) = topic_map
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
        if topic==None:
            topic = 'default'
        subscribers = self.__subscribers__[topic]
        try:
            for s in subscribers:
                s.on_completed()
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch(e)
        del self.__subscribers__[topic]

    def _dispatch_error(self, e, topic=None):
        if topic==None:
            topic = 'default'
        subscribers = self.__subscribers__[topic]
        try:
            for s in subscribers:
                s.on_error(e)
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch(e)
        del self.__subscribers__[topic]

    def _observe(self):
        # Get an event and call the appropriate dispatch function.
        raise NotImplemented

class StopSensor(Exception):
    pass

class SensorPub(Publisher):
    __slots__ = ('sensor', 'sensor_id')
    def __init__(self, sensor, sensor_id):
        super().__init__(None)
        self.sensor = sensor
        self.sensor_id = sensor_id
    def _observe(self):
        try:
            self._dispatch_next((self.sensor_id, utime.time(), self.sensor.sample()),)
        except FatalError:
            raise
        except StopSensor:
            self._dispatch_completed()
        except Exception as e:
            self._dispatch_error(e)

class _Interval:
    __slots__ = ('ticks', 'tasks', 'next_tick')
    def __init__(self, ticks, next_tick):
        self.ticks = ticks
        self.tasks = []
        self.next_tick = next_tick

class Scheduler:
    __slots__ = ('clock_wrap', 'time_in_ticks', 'intervals', 'sorted_ticks')
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
        for i in self.intervals.values():
            if task in i.tasks:
                i.tasks.remove(task)
                if len(i.tasks)==0:
                    self.sorted_ticks.remove(i.ticks)
                    del self.intervals[i.ticks]
                return
        assert 0, "Did not find task %s" % task

    def _get_next_sleep_interval(self):
        assert len(self.intervals)>0
        sleep_time = self.clock_wrap
        for i in self.intervals.values():
            time_diff = max(i.next_tick-self.time_in_ticks, 0)
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
            for i in self.intervals.values():
                if i.next_tick >= self.clock_wrap:
                    i.next_tick = i.next_tick % self.clock_wrap
                else: # interval overdue
                    i.next_tick = self.time_in_ticks - (unwrapped_time-i.next_tick)
                    
    def _get_tasks(self): # get runnable tasks
        sample_list = []
        for ticks in self.sorted_ticks:
            i = self.intervals[ticks]
            if i.next_tick<=self.time_in_ticks:
                sample_list.extend(i.tasks)
                i.next_tick = i.next_tick + i.ticks
        return sample_list

    def schedule_periodic(self, publisher, interval):
        self._add_task(publisher, interval)
        def cancel():
            self._remove_task(publisher)
        return cancel

    def schedule_sensor(self, sensor, sensor_id, interval, *subs):
        task = SensorPub(sensor, sensor_id)
        for s in subs:
            task.subscribe(s)
        return self.schedule_periodic(task, interval)
    
    def run_forever(self):
        assert len(self.intervals)>0
        while True:
            publishers = self._get_tasks()
            start_ts = utime.time()
            for pub in publishers:
                pub._observe()
                if not pub.__subscribers__:
                    self._remove_task(pub)
            if len(self.intervals)==0:
                break
            end_ts = utime.time()
            if end_ts > start_ts:
                self._advance_time(end_ts-start_ts)
            sleep = self._get_next_sleep_interval()
            utime.sleep(sleep)
            now = utime.time()
            self._advance_time(now-end_ts if now>=end_ts else sleep)
