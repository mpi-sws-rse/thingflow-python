# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Timeout-related output things and filters.
"""
from thingflow.base import OutputThing, DirectOutputThingMixin, FunctionFilter,\
                           FatalError, filtermethod

class Timeout(OutputThing, DirectOutputThingMixin):
    """An output thing that can shedule timeouts for itself. When a
    timeout occurs, an event is sent on the default port.
    The timeout_thunk is called to get the actual event.
    """
    def __init__(self, scheduler, timeout_thunk):
        super().__init__()
        self.scheduler = scheduler
        self.timeout_thunk = timeout_thunk
        self.cancel = None

    def start(self, interval):
        if self.cancel:
            self.cancel()
        self.cancel = self.scheduler.schedule_later_one_time(self, interval)

    def clear(self):
        if self.cancel:
            self.cancel()
            self.cancel = None
        
    def _observe(self):
        """If this gets called, we hit the timeout
        """
        self.cancel = None
        self._dispatch_next(self.timeout_thunk())

class EventWatcher:
    """Watch the event stream and then produce an event for a timeout
    when asked. This can be subclassed to implement different
    policies.
    """
    def on_next(self, x):
        pass # we get a regular event
    def produce_event_for_timeout(self):
        return None # return the timeout event
    def close(self): # called for on_completed or on_error
        pass

    
class SupplyEventWhenTimeout(FunctionFilter):
    """This filter sits in a chain and passes incoming events through to
    its output. It also passes all events to the on_next() method of the
    event watcher. If no event arrives on the input after the interval has
    passed since the last event, event_watcher.produce_event_for_timeout()
    is called to get a dummy event, which is passed upstream.
    """
    def __init__(self, previous_in_chain, event_watcher, scheduler, interval):
        self.event_watcher = event_watcher
        self.timeout_thing = \
            Timeout(scheduler, self.event_watcher.produce_event_for_timeout)
        self.interval = interval
        def on_next(self, x):
            self.event_watcher.on_next(x)
            # reset the timer
            self.timeout_thing.start(self.interval)
            self._dispatch_next(x)
        def on_completed(self):
            self.event_watcher.close()
            self.timeout_thing.clear()
            self._dispatch_completed()
        def on_error(self, e):
            self.event_watcher.close()
            self.timeout_thing.clear()
            self._dispatch_error(e)
        super().__init__(previous_in_chain, on_next=on_next,
                         on_completed=on_completed, on_error=on_error,
                         name='supply_event_when_timeout')
        # pass the timeout_thing's timeout events to my on_timeout_next()
        # method<
        self.timeout_thing.connect(self,
                                   port_mapping=('default','timeout'))
        # We start the timeout now - if we don't get a first event from the
        # input within the timeout, we should supply a timeout event. This
        # timeout won't start counting down until we start the scheduler.
        self.timeout_thing.start(interval)

    def on_timeout_next(self, x):
        """This method is connected to the Timeout thing's output. If it
        gets called, the timeout has fired. We need to reschedule the timeout
        as well, so that we continue to produce events in the case of multiple
        consecutive timeouts.
        """
        self.timeout_thing.start(self.interval)
        self._dispatch_next(x)

    def on_timeout_error(self, e):
        """This won't get called, as the Timeout thing does not republish any
        errors it receives.
        """
        raise FatalError("%s.on_timeout_error should not be called" % self)

    def on_timeout_completed(self):
        """This won't get called, as the timeout thing does not propate
        any completions. We just use the primary event stream to figure out when
        things are done and clear any pending timeouts at that time.
        """
        raise FatalError("%s.on_timeout_completed should not be called" % self)

@filtermethod(OutputThing)
def supply_event_when_timeout(this, event_watcher, scheduler, interval):
    return SupplyEventWhenTimeout(this, event_watcher, scheduler, interval)
