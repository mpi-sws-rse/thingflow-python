# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from antevents.base import Publisher, DirectPublisherMixin

class Never(Publisher, DirectPublisherMixin):
    """A publisher that never calls its subscribers: creates an empty stream that never goes away 
    """
    def __init__(self):
        super().__init__()

    def _observe(self):
        """Do nothing
        """
        return True
