# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from antevents.base import Publisher, Filter, filtermethod

@filtermethod(Publisher)
def map(this, xformer):
    """Map elements of a stream using the xformer.
    """
    def on_next(self, x):
        y = xformer(x)
        self._dispatch_next(y)
    return Filter(this, on_next, name="map")
