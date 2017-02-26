# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from sys import stdout

from antevents.base import Publisher, Filter, filtermethod

@filtermethod(Publisher)
def output(this, file=stdout):
    """Print each element of the sequence. Exceptions are printed
    as well. We don't call it print, because that will override the
    built-in print function.
    """
    def on_next(self, x):
        print(x, file=file)
        self._dispatch_next(x)
    def on_error(self, e):
        print(e, file=file)
        self._dispatch_error(e)
    return Filter(this, on_next, on_error=on_error, name="output")

@filtermethod(Publisher)
def output_count(this, file=stdout):
    """Just count the number of events and print out a banner with the
    total at the end.
    """
    def on_next(self, x):
        if hasattr(self, 'count'):
            self.count += 1
        else:
            setattr(self, 'count', 1)
        self._dispatch_next(x)
    def on_completed(self):
        if hasattr(self, 'count'):
            msg = "*      %d events processed      *" % self.count
        else:
            msg = "*      0 events processed      *"
        print('*'*len(msg), file=file)
        print(msg, file=file)
        print('*'*len(msg), file=file)
        self._dispatch_completed()
    return Filter(this, on_next, on_completed=on_completed, name="output_count")
