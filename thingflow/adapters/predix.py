"""
Adapters to Predix TimeSeries API

Library dependencies: websocket-client requests
"""
import logging
import json
import time
import os

from websocket import create_connection
import requests

from thingflow.base import SensorEvent, InputThing, OutputThing, FatalError

logger = logging.getLogger(__name__)

def ts_to_predix_ts(ts):
    return int(round(1000*ts))

# we use this to generate unique message ids
_PIDSTR = str(os.getpid())

class EventExtractor:
    """Methods to access data from an event for use in a
    predix ingestion message. This implementation is for the default SensorEvent
    namedtuple. Methods can be overridden or a new class created to handle
    other event data types or change functionality.
    """
    def __init__(self, quality=3, attributes=None):
        """Since we do not have a quality value in our default event type,
        we set the same quality for all datapoints. Currently the default is 3 (good),
        although they seem to recommend 1 (uncertain).
        """
        self.quality = quality
        self.attributes = attributes
        
    def get_message_id(self):
        """Not associated with the event, but with the message that will be sent.
        """
        return _PIDSTR + str(int(round(1000*time.time())))

    def get_attributes(self, sensor_id):
        """Attributes are a property of the sensor, not the individual event.
        Return either None or a dict of key/value pairs.
        """
        return self.attributes
    
    def get_sensor_id(self, event):
        return event.sensor_id

    def get_predix_timestamp(self, event):
        """Get the timestamp in miliseconds since the epoch
        """
        return ts_to_predix_ts(event.ts)

    def get_value(self, event):
        return event.val

    def get_quality(self, event):
        """See the predix documentation. 3 means good.
        """
        return self.quality

    

def _create_ingest_body(events, extractor):
    """Create the POST body for an ingest message. Accepts a list of events.
    See https://docs.predix.io/en-US/content/service/data_management/time_series/using-the-time-series-service#concept_dc613f2c-bb63-4287-9c95-8aaf2c1ca6f7 for details
    """
    mid = extractor.get_message_id()
    datapoints_by_sensor = {}
    for event in events:
        sensor_id = extractor.get_sensor_id(event)
        if sensor_id not in datapoints_by_sensor:
            datapoints_by_sensor[sensor_id] = []
        datapoints_by_sensor[sensor_id].append(
            [extractor.get_predix_timestamp(event),
             extractor.get_value(event),
             extractor.get_quality(event)])
    body = []
    for sensor_id in sorted(datapoints_by_sensor.keys()):
        body_data = {'name':str(sensor_id), 'datapoints':datapoints_by_sensor[sensor_id]}
        attributes = extractor.get_attributes(sensor_id)
        if attributes is not None:
            body_data['attributes'] = attributes
        body.append(body_data)
    return {'messageId':mid,
            'body': body}

class PredixError(Exception):
    pass

class PredixWriter(InputThing):
    """Adapter that sends mesages to the Predix TimeSeries service via the
    Ingest websocket API.

    The batch_size is used to determine how many events go into a message.

    The extractor parameter specifies a class to map from internal events to
    Predix events. The default value maps from thingflow.base.SensorEvent.
    """
    def __init__(self, ingest_url, predix_zone_id, token, batch_size=1,
                 extractor=EventExtractor()):
        self.ingest_url = ingest_url
        self.batch_size = batch_size
        self.extractor = extractor
        self.headers = {'Predix-Zone-Id': predix_zone_id,
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'}
        self.ws = None
        self.pending_events = []

    def _send(self):
        if self.ws is None:
            logging.info("Connecting to Predix...")
            self.ws = create_connection(self.ingest_url, header=self.headers)
            logging.info("Connected")
        body = json.dumps(_create_ingest_body(self.pending_events, extractor=self.extractor))
        #print(body)
        self.ws.send(body)
        result = self.ws.recv()
        rdata = json.loads(result)
        if rdata['statusCode']!=202:
            raise PredixError("Unexpected websocket response: %s" % result)
        self.pending_events = []

    def on_next(self, msg):
        self.pending_events.append(msg)
        if len(self.pending_events)==self.batch_size:
            self._send()

    def on_completed(self):
        if len(self.pending_events)>0:
            self._send()
        if self.ws:
            self.ws.close()

    def on_error(self, e):
        if len(self.pending_events)>0:
            try:
                self._send()
            except Exception as e:
                logger.exception("Error in attemping to flush pending messages to predix", e)
        if self.ws:
            self.ws.close()



def _create_query_body(sensor_id, start_time_ms, end_time_ms):
    return {
        "cache_time": 0,
        "tags": [
            {
                "name": sensor_id,
                "order": "asc"
            }
        ],
        "start": start_time_ms,
        "end": end_time_ms
    }


def build_sensor_event(sensor_id, predix_timestamp, value, quality):
    """Use the data from a predix datapoint to construct a sensor event
    """
    return SensorEvent(sensor_id, predix_timestamp/1000, value)

def _parse_query_response(resp, build_event_fn=build_sensor_event):
    try:
        l = resp['tags'][0]
        results = l['results']
        sensor_id=l['name']
        values = [build_sensor_event(sensor_id, v[0], v[1], v[2]) for v in
                  results[0]['values']]
        count = l['stats']['rawCount']
        if count>0:
            last_timestamp_ms = results[0]['values'][-1][0]
        else:
            last_timestamp_ms = None
        return count, values, last_timestamp_ms
    except Exception as e:
        logger.exception("Parse error for query response %s" % resp, e)
        raise Exception("Parse error for query response %s" % resp)
    

class PredixReader(OutputThing):
    """Query the Predix time series service for events and inject them
    into thingflow.

    The query API is a little problematic for ongoing event
    queries, as it is stateless and does not have a concept of event ids.
    Thus, we have to query for events within specific ranges. We can work
    around this by querying for one millisecond more than the last event.
    """
    def __init__(self, query_url, predix_zone_id, token, sensor_id, start_time=None,
                 one_shot=False, build_event_fn=build_sensor_event):
        """start_time is the starting time for the first query. If not specified,
        the time that the reader object was constructed is used. The end time
        for queries is always the current time.

        If one_shot is True, we just do a single query and close the stream.

        build_event_fn is a function mapping from fields of a predix timeseries
        event to internal events to be used within ThingFlow. By default, it
        maps to thingflow.base.SensorEvent tuples.
        """
        super().__init__()
        self.query_url = query_url
        self.headers = {'Predix-Zone-Id': predix_zone_id,
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'}
        self.sensor_id = sensor_id
        if start_time:
            self.start_time_ms = ts_to_predix_ts(start_time)
        else:
            self.start_time_ms = ts_to_predix_ts(time.time())
        self.one_shot = one_shot
        self.build_event_fn = build_sensor_event
        

    def _query(self, start_time_ms, end_time_ms):
        body = _create_query_body(self.sensor_id, start_time_ms, end_time_ms)
        #print(body)
        r = requests.post(self.query_url, data=bytes(json.dumps(body), encoding='utf-8'),
                          headers=self.headers)
        resp = r.json()
        logger.debug("response: %s", resp)
        (count, events, last_timestamp_ms) = \
            _parse_query_response(resp, build_event_fn=self.build_event_fn)
        assert count==len(events)
        r.close()
        return events, last_timestamp_ms
        
    def _observe(self):
        query_time_ms = ts_to_predix_ts(time.time())
        try:
            (events, last_timestamp_ms) = self._query(self.start_time_ms, query_time_ms)
            for event in events:
                self._dispatch_next(event)
        except FatalError:
            raise
        except Exception as e:
            logger.exception("Got an error during query", e)
            self._dispatch_error(e)
            return
        if self.one_shot:
            logger.info("Done with data from %s" % self.sensor_id)
            self._dispatch_completed()
            return
        # if not one shot, we use the last timestamp time + 1 tick
        # as the next start time.
        # If no events were found, we leave the same start time
        if len(events)>0:
            self.start_time_ms =  last_timestamp_ms + 1
            
            
