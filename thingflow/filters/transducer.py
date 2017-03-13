# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Transducers for streams.
A transducer maintains internal state which is updated every time 
on_next is called. It implements a function
f: Input X State -> Output X State

For those who speak automata, this is a Mealy machine.
"""
from collections import deque
from statistics import median

from thingflow.base import OutputThing, XformOrDropFilter, SensorEvent, filtermethod


class Transducer:
    def __init__(self):
        pass
    def step(self, v):
        return v # return the transformed value

    def complete(self):
        """Can optionally return a final value
        """
        pass

class Transduce(XformOrDropFilter):
    def __init__(self, previous_in_chain, xformer):
        super().__init__(previous_in_chain)
        self.xformer = xformer

    def _filter(self, x):
        return self.xformer.step(x)

    def _complete(self):
        return self.xformer.complete()

    def __str__(self):
        return "transduce(%s)" % self.xformer


@filtermethod(OutputThing)
def transduce(this, xform):
    """Execute a (stateful) transducer to transform the event sequence.
    The transducer provides a step() method to accept a value
    and return the transformation. If the step() returns None,
    no output event is emitted

    Arguments:
    :param Transducer transducer: A transducer to execute.

    :returns: An OutputThing sequence containing the results from the
        transducer.
    :rtype: OutputThing
    """
    return Transduce(this, xform)


class SlidingWindowTransducer(Transducer):
    """Transducer that processses a sliding window of events. The most recent
    history_samples events are kept internally in a deque. When an event
    arrives, it is pushed onto the deque and an old event is popped off.
    There are three cases: the very first event, events before the buffer
    is full, and events after the buffer is full. For each case, the new
    event, old event (if one is being popped off), and a accumulated state value
    are passed to a template method. The method returns the transduced event
    and a new value for the accumulated state. This makes it easy to
    efficently implement algorithms like a running average or min/max, etc.

    Note that the window here is based on the number of samples, not a time
    period.
    """
    def __init__(self, history_samples):
        self.history_samples = history_samples
        self.history = deque(maxlen=history_samples)
        self.state = None

    def step(self, event):
        if len(self.history)==0:
            (output_event, self.state) = self._first_event(event)
            self.history.append(event)
        elif len(self.history)<self.history_samples:
            (output_event, self.state) = self._add_event(self.state, event,
                                                         len(self.history)+1)
            self.history.append(event)
        else:
            assert len(self.history)==self.history_samples
            old_event = self.history.popleft()
            (output_event, self.state) = self._replace_event(self.state, event,
                                                             old_event, self.history_samples)
            self.history.append(event)

        return output_event

    def _first_event(self, new_event):
        """Called when the first event is received. Should return a pair
        consisting of the output event and new state.
        """
        raise NotImplemented

    def _add_event(self, state, new_event, total_events):
        """Called when we have an initial state, but the history buffer is not
        yet full. Thus, we'll be adding to the buffer, Should return a pair
        consisting of the output event and new state.
        """
        raise NotImplemented

    def _replace_event(self, state, new_event, old_event, total_events):
        """Called when the buffer is full. We are evicting old_event to make
        room for new_event. The total size of the buffer will then be
        total_events. Should return a pair consisting of the output event and
        new state.
        """
        raise NotImplemented
    

class SensorSlidingMean(SlidingWindowTransducer):
    """Given a stream of SensorEvents, output a new
    event representing the mean of the event values in the
    window. The state we keep is the sum of the .val fields within
    the window. We assume that all events are from the same sensor.
    """
    def __init__(self, history_samples):
        super().__init__(history_samples)

    def _first_event(self, new_event):
        return (new_event, new_event.val)

    def _add_event(self, state, new_event, total_events):
        new_state = state + new_event.val
        new_event = SensorEvent(sensor_id=new_event.sensor_id,
                                ts=new_event.ts,
                                val=(new_state)/total_events)
        return (new_event, new_state)

    def _replace_event(self, state, new_event, old_event, total_events):
        new_state = state + new_event.val - old_event.val
        new_event = SensorEvent(sensor_id=new_event.sensor_id,
                                ts=new_event.ts,
                                val=(new_state)/total_events)
        return (new_event, new_state)
        
    def __str__(self):
        return 'SensorSlidingMean(%d)' % self.history_samples


class PeriodicMedianTransducer(Transducer):
    """Emit an event once every ``period`` input events.
    The value is the median of the inputs received since the last
    emission.
    """
    def __init__(self, period=5):
        self.period = period
        self.samples = [None for i in range(period)]
        self.events_since_last = 0
        self.last_event = None # this is used in emitting the last event

    def _event_to_val(self, evt):
        """Given an event, return the sample value. The default is for
        SensorEvent. Override if you have a different event definition.
        """
        return evt.val
    
    def _make_event(self, last_event, val):
        """Return an event based off the last event, but with the specified
        value. This is for SensorEvent. Override if you have a different
        event definition.
        """
        return SensorEvent(sensor_id=last_event.sensor_id,
                           ts=last_event.ts, val=val)
    
    def step(self, v):
        self.samples[self.events_since_last] = self._event_to_val(v)
        self.events_since_last += 1
        if self.events_since_last==self.period:
            val = median(self.samples)
            event = self._make_event(v, val)
            self.events_since_last = 0
            return event
        else:
            self.last_event = v # save in case we complete before completing a period
            return None

    def complete(self):
        if self.events_since_last>0:
            # if we have some partial state, we emit one final event that
            # averages whatever we saw since the last emission.
            return self._make_event(self.last_event, median(self.samples[0:self.events_since_last]))
