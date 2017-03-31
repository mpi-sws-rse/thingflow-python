# Copyright 2016,2017 by MPI-SWS and Data-ken Research.
# Licensed under the Apache 2.0 License.
"""
This sub-module provides a collection of filters for providing linq-style
programming (inspired by RxPy).

Each function appears as a method on the OutputThing base class, allowing for
easy chaining of calls. For example::

    sensor.where(lambda x: x > 100).select(lambda x: x*2)

If the @filtermethod decorator is used, then a standalone function is also
defined that takes all the arguments except the  publisher and returns a
function which, when called, takes a publisher and subscribes to the publisher.
We call this returned function a "thunk". Thunks can be used with combinators
(like compose(), parallel(), and passthrough(), all defined in combinators.py)
as well as directly with the scheduler. For example::

    scheduler.schedule_sensor(sensor, where(lambda x: x> 100),
                                      select(lambda x: x*2))


The implementation code for a linq-style filter typically looks like the
following::

    @filtermethod(OutputThing)
    def example(this, ...):
        def _filter(self, x):
            ....
        return FunctionFilter(this, _filter, name="example")

Note that, by convention, we use `this` as the first argument of the function,
rather than self. The `this` parameter corresponds to the previous element in
the chain, while the `self` parameter used in the _filter() function represents
the current element in the chain. If you get these mixed up, you can get an
infinite loop!

In general, a linq-style filter takes the previous OutputThing/filter in a
chain as its first input, parameters to the filter as subsequent inputs, and
returns a OutputThing/filter that should be used as the input to the next step
in the filter chain.
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
from . import combinators
