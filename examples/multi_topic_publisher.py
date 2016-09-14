"""A simple example to demonstrate publishing on multiple topics. The 
publisher samples values from a sensor and publishes them on different output
ports depending on the divisibility of the value. See docs/pubsub-topics.rst
for a more detailed explanation.
"""
import random
import asyncio
from antevents.base import Publisher, DirectPublisherMixin, Scheduler, FatalError

class MultiTopicPublisher(Publisher, DirectPublisherMixin):
    def __init__(self, sensor):
        super().__init__(topics=['divisible_by_two', 'divisible_by_three',
                                 'other'])
        self.sensor = sensor
        
    def _observe(self):
        try:
            val = int(round(self.sensor.sample()))
            if (val%2)==0:
                self._dispatch_next(val, topic='divisible_by_two')
            if (val%3)==0:
                self._dispatch_next(val, topic='divisible_by_three')
            if (val%3)!=0 and (val%2)!=0:
                self._dispatch_next(val, topic='other')
                
        except FatalError:
            raise
        except StopIteration:
            self._dispatch_completed(topic='divisible_by_two')
            self._dispatch_completed(topic='divisible_by_three')
            self._dispatch_completed(topic='other')
        except Exception as e:
            self._dispatch_error(e, topic='divisible_by_two')
            self._dispatch_error(e, topic='divisible_by_three')
            self._dispatch_error(e, topic='other')
    
    def __repr__(self):
        return 'MultiTopicPublisher()'

class RandomSensor:
    def __init__(self, sensor_id, mean=100.0, stddev=20.0, stop_after_events=None):
        self.sensor_id = sensor_id
        self.mean = mean
        self.stddev = stddev
        self.stop_after_events = stop_after_events
        if stop_after_events is not None:
            def generator():
                for i in range(stop_after_events):
                    yield random.gauss(mean, stddev)
        else: # go on forever
            def generator():
                while True:
                    yield random.gauss(mean, stddev)
        self.generator = generator()

    def sample(self):
        return self.generator.__next__()

    def __repr__(self):
        if self.stop_after_events is None:
            return 'RandomSensor(%s, mean=%s, stddev=%s)' % \
                (self.sensor_id, self.mean, self.stddev)
        else:
            return 'RandomSensor(%s, mean=%s, stddev=%s, stop_after_events=%s)' % \
                (self.sensor_id, self.mean, self.stddev, self.stop_after_events)


scheduler = Scheduler(asyncio.get_event_loop())
sensor = RandomSensor(1, mean=10, stddev=5, stop_after_events=10)
pub = MultiTopicPublisher(sensor)
pub.subscribe(lambda v: print("even: %s" % v),
              topic_mapping=('divisible_by_two', 'default'))
pub.subscribe(lambda v: print("divisible by three: %s" % v),
              topic_mapping=('divisible_by_three', 'default'))
pub.subscribe(lambda v: print("not divisible: %s" % v),
              topic_mapping=('other', 'default'))
scheduler.schedule_recurring(pub)
scheduler.run_forever()

