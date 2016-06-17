"""Adapters for reading/writing event streams to CSV (spreadsheet) files.
"""

"""Define an event type for time-series data from sensors.
from collections import namedtuple

# Define a sensor event as a tuple of sensor id, timestamp, and value.
# A 'sensor' is just a generator of sensor events.
SensorEvent = namedtuple('SensorEvent', ['sensor_id', 'ts', 'val'])

"""
import datetime
import csv as csvlib
import logging
logger = logging.getLogger(__name__)

from antevents.base import DefaultSubscriber, Publisher, FatalError
from antevents.internal import extensionmethod
from antevents.sensor import SensorEvent
from antevents.adapters.generic import EventRowMapping, DirectReader

class EventSpreadsheetMapping(EventRowMapping):
    """Define the mapping between an event record and a spreadsheet.
    """
    def get_header_row(self):
        """Return a list of header row column names.
        """
        raise NotImplemented


    
class SensorEventMapping(EventSpreadsheetMapping):
    """A maping that works for SensorEvent tuples. We map the time
    values twice - as the raw timestamp and as an iso-formatted datetime.
    """
    def get_header_row(self):
        return ['timestamp', 'datetime', 'sensor_id', 'value']

    def event_to_row(self, event):
        return [event.ts,
                datetime.datetime.utcfromtimestamp(event.ts).isoformat(),
                event.sensor_id,
                event.val]

    def row_to_event(self, row):
        ts = float(row[0])
        sensor_id = int(row[2])
        val = float(row[3])
        return SensorEvent(ts=ts, sensor_id=sensor_id, val=val)
    
default_event_mapper = SensorEventMapping()


class CsvWriter(DefaultSubscriber):
    def __init__(self, previous_in_chain, filename,
                 mapper=default_event_mapper):
        self.filename = filename
        self.mapper = mapper
        self.file = open(filename, 'w', newline='')
        self.writer = csvlib.writer(self.file)
        self.writer.writerow(self.mapper.get_header_row())
        self.file.flush()
        self.dispose = previous_in_chain.subscribe(self)

    def on_next(self, x):
        self.writer.writerow(self.mapper.event_to_row(x))
        self.file.flush()

    def on_completed(self):
        self.file.close()

    def on_error(self, e):
        self.file.close()

    def __str__(self):
        return 'csv_writer(%s)' % self.filename

@extensionmethod(Publisher)
def csv_writer(this, filename, mapper=default_event_mapper):
    """Write an event stream to a csv file. mapper is an
    instance of EventSpreadsheetMapping.
    """    
    return CsvWriter(this, filename, mapper)



class CsvReader(DirectReader):
    def __init__(self, filename, mapper=default_event_mapper,
                 has_header_row=True):
        """Creates a publisher that reads a row at a time from a csv file
        and converts the rows into events using the specified mapping.
        """
        self.filename = filename
        self.file = open(filename, 'r', newline='')
        reader = csvlib.reader(self.file)
        if has_header_row:
            # swallow up the header row so it is not passed as data
            try:
                header_row = reader.__next__()
                logger.debug("header row of %s: %s", filename, ', '.join(header_row))
            except:
                raise FatalError("Problem in reading header row of csv file %s" % filename)
        super().__init__(reader, mapper, name='CsvReader(%s)'%filename)

    def _close(self):
        self.file.close()
