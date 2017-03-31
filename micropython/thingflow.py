
# thingflow for micropython

from ucollections import namedtuple
import utime

class FatalError(Exception):
    pass

class ExcInDispatch(FatalError):
    # Dispatching an event should not raise an error, other than a fatal error.
    pass


_Connection = namedtuple('_Connection', ['on_next', 'on_completed', 'on_error'])

# Base class for event generators (output_things).
class OutputThing:
    __slots__ = ('__connections__',)
    def __init__(self, ports=None):
        self.__connections__ = {}
        if ports==None:
            ports = ['default']
        for port in ports:
            self.__connections__[port] = []

    def connect(self, input_thing, port_map=None):
        if port_map==None:
            out_port = 'default'
            in_port = 'default'
        else:
            (out_port, in_port) = port_map
        if in_port=='default':
            dispatchnames = ('on_next', 'on_completed', 'on_error')
        else:
            dispatchnames = ('on_%s_next' % in_port,
                             'on_%s_completd' % in_port,
                             'on_%s_error' % in_port)
        functions = [getattr(input_thing, m) for m in dispatchnames]
        connection = _Connection(on_next=functions[0],
                                 on_completed=functions[1],
                                 on_error=functions[2])
        new_connections = self.__connections__[out_port].copy()
        new_connections.append(connection)
        self.__connections__[out_port] = new_connections
        def dispose():
            new_connections = self.__connections__[out_port].copy()
            new_connections.remove(connection)
            self.__connections__[out_port] = new_connections
        return dispose

    def _dispatch_next(self, x, port=None):
        connections = self.__connections__[port if port is not None
                                           else 'default']
        try:
            for s in connections:
                s.on_next(x)
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch(e)

    def _dispatch_completed(self, port=None):
        if port==None:
            port = 'default'
        connections = self.__connections__[port]
        try:
            for s in connections:
                s.on_completed()
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch(e)
        del self.__connections__[port]

    def _dispatch_error(self, e, port=None):
        if port==None:
            port = 'default'
        connections = self.__connections__[port]
        try:
            for s in connections:
                s.on_error(e)
        except FatalError:
            raise
        except Exception as e:
            raise ExcInDispatch(e)
        del self.__connections__[port]

    def _observe(self):
        # Get an event and call the appropriate dispatch function.
        raise NotImplemented


class SensorAsOutputThing(OutputThing):
    __slots__ = ('sensor')
    def __init__(self, sensor):
        super().__init__(None)
        self.sensor = sensor
    def _observe(self):
        try:
            v = self.sensor.sample()
            self._dispatch_next((self.sensor.sensor_id, utime.time(), v),)
        except FatalError:
            raise
        except StopIteration:
            self._dispatch_completed()
        except Exception as e:
            self._dispatch_error(e)

class Output:
    def on_next(self, x):
        print(x)
    def on_completed():
        pass
    def on_error(self, e):
        print("Error: " + e)

class _Interval:
    __slots__ = ('ticks', 'tasks', 'next_tick')
    def __init__(self, ticks, next_tick):
        self.ticks = ticks
        self.tasks = []
        self.next_tick = next_tick

class Scheduler:
    __slots__ = ('clock_wrap', 'time_in_ticks', 'intervals', 'sorted_ticks')
    def __init__(self, clock_wrap=1048576):
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

    def schedule_periodic(self, output_thing, interval):
        interval_ticks = int(round(interval*100))
        assert interval_ticks>0
        self._add_task(output_thing, interval_ticks)
        def cancel():
            self._remove_task(output_thing)
        return cancel

    def schedule_sensor(self, sensor, interval, *conns):
        task = SensorAsOutputThing(sensor)
        for s in conns:
            task.connect(s)
        return self.schedule_periodic(task, interval)
    
    def run_forever(self):
        assert len(self.intervals)>0
        while True:
            output_things = self._get_tasks()
            start_ts = utime.ticks_ms()
            for pub in output_things:
                pub._observe()
                if not pub.__connections__:
                    self._remove_task(pub)
            if len(self.intervals)==0:
                break
            end_ts = utime.ticks_ms()
            if end_ts > start_ts:
                self._advance_time(int(round((end_ts-start_ts)/10)))
            sleep = self._get_next_sleep_interval()
            utime.sleep_ms(sleep*10)
            now = utime.ticks_ms()
            self._advance_time(int(round((now-end_ts)/10)) if now>=end_ts else sleep)
