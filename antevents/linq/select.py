from antevents.base import Publisher, Filter, filtermethod


@filtermethod(Publisher, alias="map")
def select(this, mapfun):
    """Returns a stream whose elements are the result of
    invoking the transform function on each element of source.
    """
    def on_next(self, x):
        self._dispatch_next(mapfun(x))
    return Filter(this, on_next, name="select")
