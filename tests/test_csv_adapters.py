"""Verify the csv reader/writer through a round trip
"""

import unittest
import time
from tempfile import NamedTemporaryFile
import os
import asyncio
import datetime

from antevents.base import Scheduler, IterableAsPublisher, SensorEvent
from antevents.adapters.csv import CsvReader, default_event_mapper
import antevents.linq.dispatch
from utils import make_test_publisher, CaptureSubscriber, \
    SensorEventValidationSubscriber

NUM_EVENTS=5

class TestCases(unittest.TestCase):
    def test_default_mapper(self):
        """Verify the class that maps between an event and a sensor
        """
        event = SensorEvent(ts=time.time(), sensor_id=1, val=123.456)
        row = default_event_mapper.event_to_row(event)
        event2 = default_event_mapper.row_to_event(row)
        self.assertEqual(event2, event,
                         "Round-tripped event does not match original event")

    def test_file_write_read(self):
        tf = NamedTemporaryFile(mode='w', delete=False)
        tf.close()
        try:
            sensor = make_test_publisher(1, stop_after_events=NUM_EVENTS)
            capture = CaptureSubscriber()
            sensor.subscribe(capture)
            sensor.csv_writer(tf.name)
            scheduler = Scheduler(asyncio.get_event_loop())
            scheduler.schedule_recurring(sensor)
            print("Writing sensor events to temp file")
            scheduler.run_forever()
            self.assertTrue(capture.completed, "CaptureSubscriber did not complete")
            self.assertEqual(len(capture.events), NUM_EVENTS,
                             "number of events captured did not match generated events")
            reader = CsvReader(tf.name)
            vs = SensorEventValidationSubscriber(capture.events, self)
            reader.subscribe(vs)
            scheduler.schedule_recurring(reader)
            print("reading sensor events back from temp file")
            scheduler.run_forever()
            self.assertTrue(vs.completed, "ValidationSubscriber did not complete")
        finally:
            os.remove(tf.name)

# data for rollover test
ROLLING_FILE1 = 'dining-room-2015-01-01.csv'
ROLLING_FILE2 = 'dining-room-2015-01-02.csv'
FILES = [ROLLING_FILE1, ROLLING_FILE2]
def make_ts(day, hr, minute):
    return (datetime.datetime(2015, 1, day, hr, minute) - datetime.datetime(1970,1,1)).total_seconds()
EVENTS = [SensorEvent('dining-room', make_ts(1, 11, 1), 1),
          SensorEvent('dining-room', make_ts(1, 11, 2), 2),
          SensorEvent('dining-room', make_ts(2, 11, 1), 3),
          SensorEvent('dining-room', make_ts(2, 11, 2), 4)]

# data for dispatch test
sensor_ids = ['dining-room', 'living-room']
ROLLING_FILE3 = 'living-room-2015-01-01.csv'
ROLLING_FILE4 = 'living-room-2015-01-02.csv'
FILES2 = [ROLLING_FILE1, ROLLING_FILE2, ROLLING_FILE3, ROLLING_FILE4]
EVENTS2 = [SensorEvent('dining-room', make_ts(1, 11, 1), 1),
           SensorEvent('living-room', make_ts(1, 11, 2), 2),
           SensorEvent('living-room', make_ts(2, 11, 1), 3),
           SensorEvent('dining-room', make_ts(2, 11, 2), 4)]
def make_rule(sensor_id):
    return (lambda evt: evt.sensor_id==sensor_id, sensor_id)
dispatch_rules = [make_rule(s) for s in sensor_ids]


class TestRollingCsvWriter(unittest.TestCase):
    def _cleanup(self):
        for f in FILES2:
            if os.path.exists(f):
                os.remove(f)

    def setUp(self):
        self._cleanup()

    def tearDown(self):
        self._cleanup()
        
    def test_rollover(self):
        def generator():
            for e in EVENTS:
                yield e
        sensor = IterableAsPublisher(generator(), name='sensor')
        sensor.rolling_csv_writer('.', 'dining-room')
        vs = SensorEventValidationSubscriber(EVENTS, self)
        sensor.subscribe(vs)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_recurring(sensor)
        scheduler.run_forever()
        for f in FILES:
            self.assertTrue(os.path.exists(f), 'did not find file %s' % f)
            print("found log file %s" % f)

    def test_dispatch(self):
        """Test a scenario where we dispatch to one of several writers
        depending on the sensor id.
        """
        def generator():
            for e in EVENTS2:
                yield e
        sensor = IterableAsPublisher(generator(), name='sensor')
        dispatcher = sensor.dispatch(dispatch_rules)
        for s in sensor_ids:
            dispatcher.rolling_csv_writer('.', s, sub_topic=s)
        dispatcher.subscribe(lambda x: self.assertTrue(False, "bad dispatch of %s" % x))
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_recurring(sensor)
        scheduler.run_forever()
        for f in FILES2:
            self.assertTrue(os.path.exists(f), 'did not find file %s' % f)
            cnt = 0
            with open(f, 'r') as fobj:
                for line in fobj:
                    cnt +=1
            self.assertEqual(2, cnt, "File %s did not have 2 lines" % f)
            print("found log file %s" % f)
        


if __name__ == '__main__':
    unittest.main()
        
        
