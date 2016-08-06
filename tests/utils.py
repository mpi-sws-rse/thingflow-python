"""Common utilities for the tests
"""
import time
import random
random.seed()

from antevents.base import IterableAsPublisher, DefaultSubscriber, FatalError,\
     SensorEvent

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


class ValueListSensor:
    def __init__(self, sensor_id, values):
        self.sensor_id = sensor_id
        def generator():
            for v in values:
                yield v
        self.generator = generator()

    def sample(self):
        return self.generator.__next__()

    def __repr__(self):
        return 'ValueListSensor(%s)' % self.sensor_id


def make_test_publisher(sensor_id, mean=100.0, stddev=20.0, stop_after_events=None):
    """Here is an exmple test publisher that generates a random value"""
    if stop_after_events is not None:
        def generator():
            for i in range(stop_after_events):
                yield SensorEvent(sensor_id, time.time(),
                                  random.gauss(mean, stddev))
    else: # go on forever
        def generator():
            while True:
                yield SensorEvent(sensor_id, time.time(),
                                  random.gauss(mean, stddev))
    g =  generator()
    o = IterableAsPublisher(g, name='Sensor(%s)' % sensor_id)
    return o


def make_test_publisher_from_vallist(sensor_id, values):
    """Create a publisher that generates the list of values when sampled, but uses
    real timestamps.
    """
    def generator():
        for val in values:
            yield SensorEvent(sensor_id, time.time(), val)
    o = IterableAsPublisher(generator(), name='Sensor(%s)' % sensor_id)
    return o


class ValidationSubscriber(DefaultSubscriber):
    """Compare the values in a event stream to the expected values.
    Use the test_case for the assertions (for proper error reporting in a unit
    test).
    """
    def __init__(self, expected_stream, test_case,
                 extract_value_fn=lambda event:event.val):
        self.expected_stream = expected_stream
        self.next_idx = 0
        self.test_case = test_case
        self.extract_value_fn = extract_value_fn
        self.completed = False

    def on_next(self, x):
        tc = self.test_case
        tc.assertLess(self.next_idx, len(self.expected_stream),
                      "Got an event after reaching the end of the expected stream")
        expected = self.expected_stream[self.next_idx]
        actual = self.extract_value_fn(x)
        tc.assertEqual(actual, expected,
                       "Values for element %d of event stream mismatch" % self.next_idx)
        self.next_idx += 1

    def on_completed(self):
        tc = self.test_case
        tc.assertEqual(self.next_idx, len(self.expected_stream),
                       "Got on_completed() before end of stream")
        self.completed = True

    def on_error(self, exc):
        tc = self.test_case
        tc.assertTrue(False,
                      "Got an unexpected on_error call with parameter: %s" % exc)

        
class SensorEventValidationSubscriber(DefaultSubscriber):
    """Compare the full events in a sensor event stream to the expected events.
    Use the test_case for the assertions (for proper error reporting in a unit
    test).
    """
    def __init__(self, expected_sensor_events, test_case):
        self.expected_sensor_events = expected_sensor_events
        self.next_idx = 0
        self.test_case = test_case
        self.completed = False

    def on_next(self, x):
        tc = self.test_case
        tc.assertLess(self.next_idx, len(self.expected_sensor_events),
                      "Got an event after reaching the end of the expected stream")
        expected = self.expected_sensor_events[self.next_idx]
        actual = x
        tc.assertEqual(actual.val, expected.val,
                       "Values for element %d of event stream mismatch" % self.next_idx)
        tc.assertEqual(actual.sensor_id, expected.sensor_id,
                       "sensor ids for element %d of event stream mismatch" % self.next_idx)
        # since the timestamp is a floating point number, we only check that
        # the timestamps are "close enough"
        tc.assertAlmostEqual(actual.ts, expected.ts, places=5,
                             msg="Timestamps for element %d of event stream mismatch" % self.next_idx)
        self.next_idx += 1

    def on_completed(self):
        tc = self.test_case
        tc.assertEqual(self.next_idx, len(self.expected_sensor_events),
                       "Got on_completed() before end of stream")
        self.completed = True

    def on_error(self, exc):
        tc = self.test_case
        tc.assertTrue(False,
                      "Got an unexpected on_error call with parameter: %s" % exc)


class CaptureSubscriber(DefaultSubscriber):
    """Capture the sequence of events in a list for later use.
    """
    def __init__(self):
        self.events = []
        self.completed = False

    def on_next(self, x):
        self.events.append(x)

    def on_completed(self):
        self.completed = True

    def on_error(self, e):
        raise FatalError("Should not get on_error, got on_error(%s)" % e)
