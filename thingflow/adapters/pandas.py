# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
Pandas (http://pandas.pydata.org) is a data analysis library.
This module contains adapters for converting between thingflow
event streams and Pandas data types.
"""
import datetime
import pandas as pd

from thingflow.base import InputThing

class PandasSeriesWriter(InputThing):
    """Create a pandas Series object corresponding to the
    event stream passed to this subscriber.
    """
    def __init__(self, tz=datetime.timezone.utc):
        self.data= []
        self.index = []
        self.tz = tz
        self.result = None # we will store the series here when done
        
    def on_next(self, x):
        self.data.append(x.val)
        self.index.append(datetime.datetime.fromtimestamp(x.ts, tz=self.tz))

    def on_completed(self):
        self.result = pd.Series(self.data, index=self.index)


