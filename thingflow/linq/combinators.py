# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
This module defines combinators for linq-style functions:
compose, parallel, and passthrough. A linq-style function takes the previous
publisher/filter in a chain as its first input ("this"), parameters to the
filter as subsequent inputs, and returns a publisher/filter that should be
used as the input to the next step in the filter chain.

We use the term "thunk" for the special case where the linq-style function
takes only a single input - the previous publisher/filter in the chain.
The Scheduler.schedule_sensor() method and the functions below can accept
thunks in place filters. If a linq-style filter F was defined using
the @filtermethod decorator, then calling the function directly (not as
a method of a Publisher) returns a thunk.
"""

from antevents.base import Publisher, filtermethod, _make_thunk, \
                           _subscribe_thunk


def compose(*thunks):
    """Given a list of thunks and/or filters, compose them
    in a sequence and return a thunk.
    """
    def apply(this):
        p = this
        for thunk in thunks:
            assert p, \
                "attempted to compose a terminal subscriber/thunk in non-final position"
            p = _subscribe_thunk(p, thunk)
        return p
    _make_thunk(apply)
    return apply


def parallel(*subscribers):
    """Take one or more subscribers/thunks and create a thunk that will
    subscribe all of them to "this" when evaluated. Note that the entire
    set of subscribers acts as spurs - the original publisher is returned
    as the next publisher in the chain.
    """
    def apply(this):
        for s in subscribers:
            _subscribe_thunk(this, s)
        return this
    _make_thunk(apply)
    return apply


@filtermethod(Publisher)
def passthrough(this, spur):
    """We wish to have a spur off a chain of filters. For example, a writer that
    is a subscriber, but does not implement the publisher API. Thus, we have no
    way to put it in the middle of a chain. Or, we might want to implement a
    "fork" in the chain of filters, with two parallel downstream chains.
    
    passthrough takes "this", the previous publisher in the chain, and "spur",
    either a subscriber, a thunk (a function that takes the publisher as its
    single argument), or a plain anonymous function. The spur is subscribed to
    the publisher and then the publisher is returned to continue the chain.
    """
    _subscribe_thunk(this, spur)
    return this

