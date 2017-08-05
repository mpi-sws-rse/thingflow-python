"""
Test of timeseries ingestion
See http://predix01.cloud.answerhub.com/questions/21920/time-series-3.html?childToView=21931#answer-21931
and https://www.predix.io/resources/tutorials/tutorial-details.html?tutorial_id=1549&tag=1613&journey=Exploring%20Security%20services&resources=1594,1593,2105,1544,1549,2255,1951
"""
import logging
import time
import asyncio
import unittest
from thingflow.base import InputThing, Scheduler
from utils import make_test_output_thing_from_vallist

try:
    from config_for_tests import PREDIX_TOKEN, PREDIX_ZONE_ID, \
                                 PREDIX_INGEST_URL,PREDIX_QUERY_URL
except ImportError:
    PREDIX_TOKEN=None
    PREDIX_ZONE_ID=None
    PREDIX_INGEST_URL=None
    PREDIX_QUERY_URL=None

try:
    import websocket
    import requests
    from thingflow.adapters.predix import *
    PREREQS_AVAILABLE = True
except ImportError:
    PREREQS_AVAILABLE = False
    
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
logging.basicConfig(level=logging.DEBUG)




VALUE_STREAM = [1, 2, 3, 4, 5]

@unittest.skipUnless(PREREQS_AVAILABLE,
                     "Predix prequisites not available")
@unittest.skipUnless(PREDIX_TOKEN is not None and PREDIX_ZONE_ID is not None and\
                     PREDIX_INGEST_URL is not None and PREDIX_QUERY_URL is not None,
                     "Predix not configured in config_for_tests.py")
class TestInput(InputThing):
    """Accept events from the predix reader and print them.
    After the specified number, disconnect.
    """
    def __init__(self, prev_in_chain, name):
        self.events = []
        self.name = name
        self.disconnect = prev_in_chain.connect(self)
        self.values = []
        
    def on_next(self, x):
        print(x)
        self.values.append(x.val)
        if len(self.values)==len(VALUE_STREAM):
            self.disconnect()
            print("TestInput %s disconnected" % self.name)

    def on_completed(self):
        print("Reader %s received %d events" % (self.name, len(self.events)))



TEST_SENSOR1 = 'test-sensor-1'
TEST_SENSOR2 = 'test-sensor-2'

@unittest.skipUnless(PREREQS_AVAILABLE,
                     "Predix prequisites not available")
@unittest.skipUnless(PREDIX_TOKEN is not None and PREDIX_ZONE_ID is not None and\
                     PREDIX_INGEST_URL is not None and PREDIX_QUERY_URL is not None,
                     "Predix not configured in config_for_tests.py")
class TestPredix(unittest.TestCase):
    def test_batching(self):
        """We write out a set of event from two simulated sensors using an odd batch size (3).
        We then read them back and verify that we got all the events.
        """
        sensor1 = make_test_output_thing_from_vallist(TEST_SENSOR1, VALUE_STREAM)
        sensor2 = make_test_output_thing_from_vallist(TEST_SENSOR2, VALUE_STREAM)
        writer = PredixWriter(PREDIX_INGEST_URL, PREDIX_ZONE_ID, PREDIX_TOKEN,
                              extractor=EventExtractor(attributes={'test':True}),
                              batch_size=3)
        sensor1.connect(writer)
        sensor2.connect(writer)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(sensor1, 0.5)
        scheduler.schedule_periodic(sensor2, 0.5)

        start_time = time.time()
        scheduler.run_forever()

        # Now we read the events back
        reader1 = PredixReader(PREDIX_QUERY_URL, PREDIX_ZONE_ID, PREDIX_TOKEN, TEST_SENSOR1,
                               start_time=start_time,
                               one_shot=False)
        reader2 = PredixReader(PREDIX_QUERY_URL, PREDIX_ZONE_ID, PREDIX_TOKEN, TEST_SENSOR2,
                               start_time=start_time,
                               one_shot=False)
        ti1 = TestInput(reader1, 'sensor-1')
        ti2 = TestInput(reader2, 'sensor-2')
        scheduler.schedule_periodic(reader1, 2)
        scheduler.schedule_periodic(reader2, 2)
        scheduler.run_forever()
        self.assertListEqual(VALUE_STREAM, ti1.values)
        self.assertListEqual(VALUE_STREAM, ti2.values)

    def test_individual(self):
        """We write out a set of event from two simulated sensors using a batch size of 1.
        We then read them back and verify that we got all the events.
        """
        sensor1 = make_test_output_thing_from_vallist(TEST_SENSOR1, VALUE_STREAM)
        sensor2 = make_test_output_thing_from_vallist(TEST_SENSOR2, VALUE_STREAM)
        writer = PredixWriter(PREDIX_INGEST_URL, PREDIX_ZONE_ID, PREDIX_TOKEN,
                              extractor=EventExtractor(attributes={'test':True}),
                              batch_size=1)
        sensor1.connect(writer)
        sensor2.connect(writer)
        scheduler = Scheduler(asyncio.get_event_loop())
        scheduler.schedule_periodic(sensor1, 0.5)
        scheduler.schedule_periodic(sensor2, 0.5)

        start_time = time.time()
        scheduler.run_forever()

        # Now we read the events back
        reader1 = PredixReader(PREDIX_QUERY_URL, PREDIX_ZONE_ID, PREDIX_TOKEN, TEST_SENSOR1,
                               start_time=start_time,
                               one_shot=False)
        reader2 = PredixReader(PREDIX_QUERY_URL, PREDIX_ZONE_ID, PREDIX_TOKEN, TEST_SENSOR2,
                               start_time=start_time,
                               one_shot=False)
        ti1 = TestInput(reader1, 'sensor-1')
        ti2 = TestInput(reader2, 'sensor-2')
        scheduler.schedule_periodic(reader1, 2)
        scheduler.schedule_periodic(reader2, 2)
        scheduler.run_forever()
        self.assertListEqual(VALUE_STREAM, ti1.values)
        self.assertListEqual(VALUE_STREAM, ti2.values)
        

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
        
