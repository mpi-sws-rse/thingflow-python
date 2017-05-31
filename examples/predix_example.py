"""
Example of Predix Time Series APIs

This sends a sequence of data points via PredixWriter and then
queries then back via PredixReader.

For hints on configuring Predix, see
https://github.com/jfischer/ge-predix-python-timeseries-example
"""
import sys
import argparse
import logging
import time
import asyncio
import random

random.seed()

from thingflow.base import Scheduler, SensorAsOutputThing
from thingflow.adapters.predix import PredixWriter, PredixReader, EventExtractor

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
logging.basicConfig(level=logging.DEBUG)


TEST_SENSOR1 = 'test-sensor-1'

class TestSensor:
    """Generate a random value for the specified number of samples.
    """
    def __init__(self, sensor_id, num_events):
        self.sensor_id = sensor_id
        self.events_remaining = num_events

    def sample(self):
        if self.events_remaining>0:
            self.events_remaining -= 1
            return random.gauss(100, 5)
        else:
            raise StopIteration

    @staticmethod
    def output_thing(sensor_id, num_events):
        return SensorAsOutputThing(TestSensor(sensor_id, num_events))

def run(args, token):
    sensor1 = TestSensor.output_thing(TEST_SENSOR1, 5)
    writer = PredixWriter(args.ingest_url, args.predix_zone_id, token,
                          extractor=EventExtractor(attributes={'test':True}),
                          batch_size=3)
    sensor1.connect(writer)
    sensor1.connect(print) # also print the event
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_periodic(sensor1, 0.5)
    
    start_time = time.time()
    scheduler.run_forever()
    
    print("Reading back events")
    reader1 = PredixReader(args.query_url, args.predix_zone_id, token,
                           TEST_SENSOR1,
                           start_time=start_time,
                           one_shot=True)
    reader1.connect(print)
    scheduler.schedule_recurring(reader1)
    scheduler.run_forever()


INGEST_URL = 'wss://gateway-predix-data-services.run.aws-usw02-pr.ice.predix.io/v1/stream/messages'
QUERY_URL='https://time-series-store-predix.run.aws-usw02-pr.ice.predix.io/v1/datapoints'
    

DESCRIPTION = \
"""Example of Predix Time Series adapters for ThingFlow.
Sends a sequence of data points via PredixWriter and then
queries them back via PredixReader."""

def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--ingest-url", default=INGEST_URL,
                        help="Websockets URL for ingest. Default is for Western US datacenter")
    parser.add_argument("--query-url", default=QUERY_URL,
                        help="HTTPS URL for query. Default is for Western US datacenter")
    parser.add_argument("--sensor-id", default="sensor-1",
                        help="Sensor id (tag name) to use. Defaults to 'sensor-1'")
    parser.add_argument("predix_zone_id", metavar="PREDIX_ZONE_ID",
                        help="Zone Id for authentication")
    parser.add_argument("token_file", metavar="TOKEN_FILE",
                        help="Filename of a file containing the bearer token for authentication")
    parsed_args = parser.parse_args(args=argv)
    try:
        with open(parsed_args.token_file, 'r') as tf:
            token = tf.read().rstrip()
    except:
        parser.error("Problem opening/reading token file %s" % parsed_args.token_file)


    run(parsed_args, token)
    print("Test successful.")
    return 0

if __name__=="__main__":
    sys.exit(main())
