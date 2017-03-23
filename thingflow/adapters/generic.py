# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
Generic reader and writer classes, to be subclassed for specific adapters.
"""

from thingflow.base import OutputThing, DirectOutputThingMixin, FatalError

class EventRowMapping:
    """Interface that converts between events and "rows"
    """
    def event_to_row(self, event):
        """Convert an event to the row representation (usually a
        list of values).
        """
        raise NotImplemented

    def row_to_event(self, row):
        """Convert a row to an event.
        """
        raise NotImplemented


class DirectReader(OutputThing, DirectOutputThingMixin):
    """A reader that can be run in the current thread (does not block
    indefinitely). Reads rows from the iterable, converts them to events
    using the mapping and passes them on.
    """
    def __init__(self, iterable, mapper, name=None):
        super().__init__()
        self.iterable = iterable
        self.mapper = mapper
        self.name = name
    
    def _observe(self):
        try:
            row = self.iterable.__next__()
            self._dispatch_next(self.mapper.row_to_event(row))
        except StopIteration:
            self._close()
            self._dispatch_completed()
        except FatalError:
            self._close()
            raise
        except Exception as e:
            self._close()
            self._dispatch_error(e)

    def _close(self):
        """This method is called when we stop the iteration, either due to
        reaching the end of the sequence or an error. It can be overridden by
        subclasses to clean up any state and release resources (e.g. closing
        open files/connections).
        """
        pass
    
    def __str__(self):
        if hasattr(self, 'name') and self.name:
            return self.name
        else:
            return super().__str__()
