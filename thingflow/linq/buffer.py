# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
import datetime

from antevents.base import Publisher, Filter, FatalError, filtermethod
from antevents.linq.timeout import Timeout, EventWatcher

@filtermethod(Publisher)
def buffer_with_count(this, count):
    """
    """
    if count < 0:
        raise FatalError

    q = [ [] ]
    num_seen = [0]

    def on_next(self, x):
        num_seen[0] += 1
        q[0].append(x)
        if num_seen[0] == count:
            self._dispatch_next(q[0])
            num_seen[0] = 0
            q[0] = []

    def on_completed(self):
        print("Buffer: on_completed")
        self._dispatch_next(q[0])
        q[0] = []
        self._dispatch_completed()

    def on_error(self, e):
        self._dispatch_next(q[0])
        q[0] = []
        self._dispatch_error(e)

    return Filter(this, on_next, on_error=on_error, on_completed=on_completed, name="buffer_with_count")

class BufferEventWatcher(EventWatcher):
    def __init__(self):
        self.q  = []
    def on_next(self, x):
        print("on_next called", datetime.datetime.now(), x)
        self.q.append(x)

    def produce_event_for_timeout(self):
        r = self.q
        print("produce_event_for_timeout called", datetime.datetime.now(), r)
        self.q = [ ] 
        return r

class BufferEventUntilTimeoutOrCount(Filter):
    """A class that passes on the events on the default channel to a buffer (maintained
       by a BufferEventWatcher). When a timeout fires, the BufferEventWatcher returns
       the buffer of all events so far.
    """
    def __init__(self, previous_in_chain, event_watcher, scheduler, interval=None, count=None):
        self.count = count
        self.seen = 0
        self.event_watcher = event_watcher
        if interval:
            self.timeout_publisher = \
                Timeout(scheduler, self.event_watcher.produce_event_for_timeout)
            self.interval = interval
        def on_next(self, x):
            self.seen += 1
            self.event_watcher.on_next(x)
            if self.count and self.seen == self.count:
                e = self.event_watcher.produce_event_for_timeout()
                self.seen = 0
                self._dispatch_next(e)
                if interval:
                    self.timeout_publisher.start(self.interval)

        def on_completed(self):
            # flush the remaining events from the event buffer
            self._dispatch_next(self.event_watcher.produce_event_for_timeout())
            self.event_watcher.close()
            if interval:
                self.timeout_publisher.clear()
            self._dispatch_completed()
        def on_error(self, e):
            # flush the remaining events from the event buffer
            self._dispatch_next(self.event_watcher.produce_event_for_timeout())
            self.event_watcher.close()
            if interval:
                self.timeout_publisher.clear()
            self._dispatch_error(e)
        super().__init__(previous_in_chain, on_next=on_next,
                         on_completed=on_completed, on_error=on_error,
                         name='buffer_until_timeout')
        if interval:
            # pass the timeout_publisher's timeout events to my on_timeout_next()
            # method
            self.timeout_publisher.subscribe(self,
                                             topic_mapping=('default','timeout'))
            # We start the timeout now.
            # This timeout won't start counting down until we start the scheduler.
            self.timeout_publisher.start(interval)

    def on_timeout_next(self, x):
        """We got the buffered events from the timeout -- send it to the subscribers
           and reset the timer
        """
        self.timeout_publisher.start(self.interval)
        self._dispatch_next(x)


    def on_timeout_error(self, e):
        raise FatalError("%s.on_timeout_error should not be called" % self)

    def on_timeout_completed(self):
        raise FatalError("%s.on_timeout_completed should not be called" % self)


@filtermethod(Publisher)
def buffer_with_time(this, interval, scheduler):
    if interval < 0:
        raise FatalError
    e = BufferEventWatcher()
    f = BufferEventUntilTimeoutOrCount(this, e, scheduler, interval=interval, count=None)
    return f
 


@filtermethod(Publisher)
def buffer_with_time_or_count(this, interval, count):
    if interval <= 0:
        raise FatalError
    if count <= 0:
        raise FatalError
    e = BufferEventWatcher()
    f = BufferEventUntilTimeoutOrCount(this, e, scheduler, interval=interval, count=count)
    return f


