# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
Build a filter that takes an input stream and dispatches to one of several
output ports based on the input value.
"""

import asyncio
import unittest

from thingflow.base import OutputThing, InputThing, Scheduler
from utils import make_test_output_thing
import thingflow.filters.where
import thingflow.filters.output

class SplitOutputThing(OutputThing, InputThing):
    """Here is a filter that takes a sequence of sensor events as its input
    and the splits it into one of three output ports: 'below' if the
    value is below one standard deviation from the mean, 'above'
    if the value is above one standard deviation from the mean, and
    'within' if the value is within a standard deviation from the mean.
    """
    def __init__(self, mean=100.0, stddev=20.0):
        OutputThing.__init__(self, ports=['above', 'below', 'within'])
        self.mean = mean
        self.stddev = stddev

    def on_next(self, x):
        val = x[2]
        if val < (self.mean-self.stddev):
            #print("split: value=%s dispatching to below" % val)
            self._dispatch_next(val, port='below')
        elif val > (self.mean+self.stddev):
            #print("split: value=%s dispatching to above" % val)
            self._dispatch_next(val, port='above')
        else:
            #print("split: value=%s dispatching to within" % val)
            self._dispatch_next(val, port='within')

    def __str__(self):
        return "SplitOutputThing"

class TestMultiplePubports(unittest.TestCase):
    def test_case(self):
        sensor = make_test_output_thing(1, stop_after_events=10)
        split= SplitOutputThing()
        sensor.connect(split)
        split.connect(lambda x: print("above:%s" % x),
                        port_mapping=('above','default'))
        split.connect(lambda x: print("below:%s" % x),
                        port_mapping=('below', 'default'))
        split.connect(lambda x: print("within:%s" % x),
                        port_mapping=('within', 'default'))

        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(sensor, 1)

        sensor.print_downstream()    
        scheduler.run_forever()
        print("that's all")

if __name__ == '__main__':
    unittest.main()

        
