# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from thingflow.base import OutputThing, FunctionFilter, filtermethod

@filtermethod(OutputThing, alias="filter")
def where(this, predicate):
    """Filter a stream based on the specified predicate function.
    """
    def on_next(self, x):
        if predicate(x):
            self._dispatch_next(x)
    return FunctionFilter(this, on_next, name="where")

