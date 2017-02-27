# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from thingflow.base import OutputThing, DirectOutputThingMixin

class Never(OutputThing, DirectOutputThingMixin):
    """An OutputThing that never calls its connections: creates an empty stream that never goes away 
    """
    def __init__(self):
        super().__init__()

    def _observe(self):
        """Do nothing
        """
        pass
