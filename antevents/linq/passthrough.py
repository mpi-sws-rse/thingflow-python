"""
A writer is just a subscriber. Here, we wrap the writer in a filter,
calling the writer for each event and then passing the events on to the
next in the stream. This is helpful when debugging or doing data analysis,
although not has performant as having the next in the line directly subscribe
to the writer's predecessor.
"""

from antevents.base import Publisher, Filter
from antevents.internal import extensionmethod

@extensionmethod(Publisher)
def passthrough(this, writer):
    def on_next(self, x):
        writer.on_next(x)
        self._dispatch_next(x)

    def on_completed(self):
        writer.on_completed()
        self._dispatch_completed()

    def on_error(self, e):
        writer.on_error(e)
        self._dispatch_error(e)

    return Filter(this, on_next=on_next, on_completed=on_completed,
                  on_error=on_error, name='passthrough(%s)' % writer)

