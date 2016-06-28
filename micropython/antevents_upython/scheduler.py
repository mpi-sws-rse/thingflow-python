"""Scheduler for periodic tasks. This scheduler is optimized for minimal
power consumption (by reducing wake-ups) rather than for robustness in the face
of tight deadlines.

For ease of testing and flexibility, the scheduler API is designed such that the
sensor sampling and the sleeps between events happen outside the scheduler. The
scheduler is responsible for determining sleep times and the set of sensors to
sample at each wakeup.

Time is measured in "ticks". The are likely seconds, but there is nothing in
the scheduler depending on that. Fractional ticks are not allowed, to account
for systems that cannot handle floating point sleep times.

This module is generic over sensors: a sensor can be any object type or an
integer id.
"""
from collections import OrderedDict

class Interval:
    __slots__ = ('ticks', 'sensors', 'next_tick')
    def __init__(self, ticks, next_tick):
        self.ticks = ticks
        self.sensors = []
        self.next_tick = next_tick

    def add_sensor(self, sensor):
        self.sensors.append(sensor)

    def remove_sensor(self, sensor):
        self.sensors.remove(sensor)

    def is_empty(self):
        return len(self.sensors)==0

def find_interval_to_synchronize(new_interval, sorted_existing_intervals):
    """Find the smallest existing interval I for which either the new interval
    is a factor of I or I is a factor of the new interval. Returns None
    otherwise.
    """
    for i in sorted_existing_intervals:
        if (i%new_interval)==0 or (new_interval%i)==0:
            return i
    return None

class Scheduler:
    __slots__ = ('clock_wrap_interval', 'time_in_ticks', 'intervals',
                 'sorted_existing_intervals')
    def __init__(self, clock_wrap_interval=65535):
        self.clock_wrap_interval = clock_wrap_interval
        self.time_in_ticks = 0
        self.intervals = OrderedDict() # map from interval num ticks to interval obj
        self.sorted_existing_intervals = [] # sorted list of existing interval ticks
        
    def add_sensor(self, sensor, ticks):
        assert ticks > 0 and ticks < self.clock_wrap_interval
        if ticks in self.intervals:
            self.intervals[ticks].sensors.append(sensor)
        else:
            # new interval. first see if there is another interval to sync with.
            interval_to_sync = find_interval_to_synchronize(ticks,
                                                            self.sorted_existing_intervals)
            if interval_to_sync is not None:
                next_tick = self.intervals[interval_to_sync].next_tick
            else:
                next_tick = self.time_in_ticks # otherwise use now
            interval = Interval(ticks, next_tick)
            interval.add_sensor(sensor)
            self.intervals[ticks] = interval
            self.sorted_existing_intervals.append(ticks)
            self.sorted_existing_intervals.sort()

    def remove_sensor(self, sensor):
        for interval in self.intervals.values():  # need to search for sensor
            if sensor in interval.sensors:
                interval.remove_sensor(sensor)
                if len(interval.sensors)==0:
                    self._remove_interval(interval)
                return
        assert 0, "Did not find sensor %s" % sensor

    def _remove_interval(self, interval):
        self.sorted_existing_intervals.remove(interval.ticks)
        del self.intervals[interval.ticks]

    def is_empty(self):
        return len(self.intervals)==0
    
    def get_next_sleep_interval(self):
        """Return an integer value representing the number of ticks to
        sleep"""
        assert len(self.intervals)>0, "No sleep interval when no sensors"
        sleep_time = self.clock_wrap_interval # start with a large number
        for interval in self.intervals.values():
            time_diff = max(interval.next_tick-self.time_in_ticks, 0)
            if time_diff < sleep_time:
                sleep_time = time_diff
        return sleep_time

    def advance_time(self, ticks):
        """Time has advanced the specified number of ticks. This should be
        called after a sleep and after sampling has taken place (assuming
        the sampling process isn't instantaneous relative to a tick).
        """
        assert ticks < self.clock_wrap_interval # bad things would happen if this fails
        self.time_in_ticks += ticks
        if self.time_in_ticks >= self.clock_wrap_interval:
            # wrap all the clocks
            unwrapped_time = self.time_in_ticks
            self.time_in_ticks = self.time_in_ticks % self.clock_wrap_interval
            for interval in self.intervals.values():
                if interval.next_tick >= self.clock_wrap_interval:
                    interval.next_tick = interval.next_tick % self.clock_wrap_interval
                else: # the interval is already overdue. We will use a negative time
                    interval.next_tick = self.time_in_ticks - \
                                         (unwrapped_time-interval.next_tick)
                    
    def get_sensors_to_sample(self):
        """Given the current time, return a list of sensor ids
        to sample. Also advances the next_tick counter for each
        of these sensors. The sample list will be returned in the same order
        every time, for a give set of sensors. The sensors are ordered by
        interval creation and then by sensor creation within the interval.
        """
        sample_list = []
        for interval in self.intervals.values():
            if interval.next_tick<=self.time_in_ticks:
                sample_list.extend(interval.sensors)
                interval.next_tick = interval.next_tick + interval.ticks
        return sample_list
    
