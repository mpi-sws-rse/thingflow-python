from antevents.internal.extensionmethod import extensionmethod
from antevents.base import Publisher, Filter

@extensionmethod(Publisher, alias="filter")
def where(this, predicate):
    """Filter a stream based on the specified predicate function.
    """
    def on_next(self, x):
        if predicate(x):
            self._dispatch_next(x)
    return Filter(this, on_next, name="where")

