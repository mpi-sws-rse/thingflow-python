# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from antevents.base import Publisher, Filter, filtermethod

@filtermethod(Publisher, alias="drop")
def skip(this, count):
    """Bypasses a specified number of elements in an event sequence
    and then returns the remaining elements.
    Keyword arguments:
    count: The number of elements to skip before returning the remaining
        elements.
    Returns an event sequence that contains the elements that occur
    after the specified index in the input sequence.
    """

    if count < 0:
        raise ArgumentOutOfRangeException()

    remaining = [count]
    def on_next(self, value):
        if remaining[0] <= 0:
            self._dispatch_next(value)
        else:
            remaining[0] -= 1

    return Filter(this, on_next=on_next, name="skip")

