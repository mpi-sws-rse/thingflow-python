# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
Transform each event in the stream. thingflow.filters.select and
thingflow.filters.map have the same functionality. Just import one -
the @filtermethod decorator will create the other as an alias.
"""
from thingflow.base import OutputThing, FunctionFilter, filtermethod

@filtermethod(OutputThing, alias="select")
def map(this, mapfun):
    """Returns a stream whose elements are the result of
    invoking the transform function on each element of source.
    If the function returns None, no event is passed downstream.
    """
    def on_next(self, x):
        y = mapfun(x)
        if y is not None:
            self._dispatch_next(y)
    return FunctionFilter(this, on_next, name='map')
