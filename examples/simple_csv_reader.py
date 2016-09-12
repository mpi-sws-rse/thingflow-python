"""
This is the example from publishers.rst. It reads a CSV-formatted spreadsheet
file and generates an event from each line. We call publishers that pull
data from an external source "readers".

There is a more flexible csv reader class defined in
antevents.adapters.csv.
"""

import csv
import sys
import asyncio
from antevents.base import Publisher, DirectPublisherMixin, Scheduler,\
                           SensorEvent, FatalError
import antevents.linq.output # load the output method on the publisher

class SimpleCsvReader(Publisher, DirectPublisherMixin):
    """A simple csv file reader. We assume that each row contains
    a timestamp, a sensor id, and a value.

    We could save some work here by subclassing from
    antevents.generic.DirectReader.
    """
    def __init__(self, filename, has_header_row=True):
        super().__init__() # Make sure the publisher class is initialized
        self.filename = filename
        self.file = open(filename, 'r', newline='')
        self.reader = csv.reader(self.file)
        if has_header_row:
            # swallow up the header row so it is not passed as data
            try:
                self.reader.__next__()
            except Exception as e:
                raise FatalError("Problem reading header row of csv file %s: %s" %
                                 (filename, e))
        
    def _observe(self):
        try:
            row = self.reader.__next__()
            event = SensorEvent(ts=float(row[0]), sensor_id=row[1],
                                val=float(row[2]))
            self._dispatch_next(event)
        except StopIteration:
            self.file.close()
            self._dispatch_completed()
        except FatalError:
            self._close()
            raise
        except Exception as e:
            self.file.close()
            self._dispatch_error(e)


# If we are running this as a script, read events from the specified
# file and print them via output().
if __name__ == '__main__':
    # check command line arguments
    if len(sys.argv)!=2:
        # did not provide filename or provided too many arguments
        sys.stderr.write("%s FILENAME\n" % sys.argv[0])
        if len(sys.argv)==1:
            sys.stderr.write("  FILENAME is a required parameter\n")
        sys.exit(1)

    reader = SimpleCsvReader(sys.argv[1])
    reader.output()
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_recurring(reader)
    scheduler.run_forever()
    sys.exit(0)

        
