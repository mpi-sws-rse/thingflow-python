# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from thingflow.base import OutputThing, FunctionFilter, FatalError, filtermethod

class ArgumentOutOfRangeException(FatalError):
    pass

class SequenceContainsNoElementsError(FatalError):
    pass

@filtermethod(OutputThing)
def take_last(this, count):
    """Takes a specified number of contiguous elements from the end of an observable sequence.
    This operator accumulates a buffer with a length enough to store
    elements count elements. Upon completion of the source sequence, this
    buffer is drained on the result sequence. This causes the elements to be
    delayed.
    Keyword arguments:
    count: The number of elements to take from the end of the sequence
    """
    q = []
    def on_next(self, x):
        q.append(x)
        if len(q) > count:
            q.pop(0)

    def on_completed(self):
        while len(q):
            v = q.pop(0)
            self._dispatch_next(v)
        self._dispatch_completed()

    return FunctionFilter(this, on_next=on_next, on_completed=on_completed)


@filtermethod(OutputThing)
def last(this, default=None):
    value = [default]
    seen_value = [False]

    def on_next(self, x):
        value[0] = x
        seen_value[0] = True

    def on_completed(self):
        if not seen_value[0] and default is None:
            self._dispatch_error(SequenceContainsNoElementsError())
        else:
            self._dispatch_next(value[0])
            self._dispatch_completed()
    return FunctionFilter(this, on_next=on_next, on_completed=on_completed,
                          name='last')

@filtermethod(OutputThing)
def take(this, count):
    """Takes a specified number of contiguous elements in an event sequence.
    Keyword arguments:
    count: The number of elements to send forward before skipping the remaining
           elements.
    """

    if count < 0:
        raise ArgumentOutOfRangeException()

    remaining = [count]
    completed = [False]

    def on_next(self, value):
        if remaining[0] > 0:
            remaining[0] -= 1
            self._dispatch_next(value)
        if remaining[0]==0 and completed[0]==False:
            completed[0] = True
            self.disconnect_from_upstream()
            self._dispatch_completed()

    def on_completed(self):
        # We may have already given a completed notification if we hit count
        # elements. On the other hand, we might still need to provide a notification
        # if the actual sequence length is less than count.
        if completed[0]==False:
            completed[0] = True
            self._dispatch_completed()

    return FunctionFilter(this, on_next=on_next, on_completed=on_completed,
                          name="take(%s)" % count)

