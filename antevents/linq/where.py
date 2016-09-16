# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from antevents.base import Publisher, Filter, filtermethod

@filtermethod(Publisher, alias="filter")
def where(this, predicate):
    """Filter a stream based on the specified predicate function.
    """
    def on_next(self, x):
        if predicate(x):
            self._dispatch_next(x)
    return Filter(this, on_next, name="where")

