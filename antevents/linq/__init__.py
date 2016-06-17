"""
This sub-module provides a collection of filters for providing linq-style
programming (inspired by RxPy).

Each function appears as a method on the Publisher base class, allowing for
easy chaining of calls. For example:
    sensor.where(lambda x: x > 100).select(lambda x: x*2)

The implementation code typically looks like the following:

@extensionmethod(Publisher)
def example(this, ...):
    def on_next(self, x):
        ....
        self._dispatch_next(...)
    return Filter(this, on_next, name="example")

Note that, by convention, we use this as the first argument of the function,
rather than self. The `this` parameter corresponds to the previous element in
the chain, while the `self` parameter used in the on_next() function represents
the current element in the chain. If you get these mixed up, you can get an
infinite loop!
"""

from . import buffer
from . import first
from . import never
from . import output
from . import scan
from . import select
from . import skip
from . import some
from . import take
from . import transducer
from . import timeout
from . import where
