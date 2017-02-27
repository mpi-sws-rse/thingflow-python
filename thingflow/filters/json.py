# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
import json

from thingflow.base import OutputThing, FunctionFilter, filtermethod

@filtermethod(OutputThing)
def to_json(this):
    """Convert the events in the stream to a json string.
    """
    def on_next(self, x):
        self._dispatch_next(json.dumps(x))
        
    return FunctionFilter(this, on_next=on_next, name='to_json')


@filtermethod(OutputThing)
def from_json(this, constructor=None):
    """Parse a sequence of json strings. If constructor is specified, the
    parsed value is passed as *args to the constructor to return the actual
    object.
    """
    def on_next(self, x):
        obj = json.loads(x)
        if constructor:
            obj = constructor(*obj)
        self._dispatch_next(obj)
        
    return FunctionFilter(this, on_next=on_next, name='from_json')

