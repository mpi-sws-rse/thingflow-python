"""
Build a filter that takes an input stream and dispatches to one of several
output topics based on the input value.
"""

import asyncio

from antevents.base import Publisher, DefaultSubscriber, Scheduler
from utils import make_test_sensor
import antevents.linq.where
import antevents.linq.output

class SplitPublisher(Publisher, DefaultSubscriber):
    """Here is a filter that takes a sequence of sensor events as its input
    and the splits it into one of three output topics: 'below' if the
    value is below one standard deviation from the mean, 'above'
    if the value is above one standard deviation from the mean, and
    'within' if the value is within a standard deviation from the mean.
    """
    def __init__(self, mean=100.0, stddev=20.0):
        Publisher.__init__(self, topics=['above', 'below', 'within'])
        self.mean = mean
        self.stddev = stddev

    def on_next(self, x):
        val = x[2]
        if val < (self.mean-self.stddev):
            #print("split: value=%s dispatching to below" % val)
            self._dispatch_next(val, topic='below')
        elif val > (self.mean+self.stddev):
            #print("split: value=%s dispatching to above" % val)
            self._dispatch_next(val, topic='above')
        else:
            #print("split: value=%s dispatching to within" % val)
            self._dispatch_next(val, topic='within')

    def __str__(self):
        return "SplitPublisher"

sensor = make_test_sensor(1, stop_after_events=10)
split= SplitPublisher()
sensor.subscribe(split)
split.subscribe(lambda x: print("above:%s" % x),
                topic_mapping=('above','default'))
split.subscribe(lambda x: print("below:%s" % x),
                topic_mapping=('below', 'default'))
split.subscribe(lambda x: print("within:%s" % x),
                topic_mapping=('within', 'default'))

scheduler = Scheduler(asyncio.get_event_loop())
scheduler.schedule_periodic(sensor, 1)

sensor.print_downstream()    
scheduler.run_forever()
print("that's all")
