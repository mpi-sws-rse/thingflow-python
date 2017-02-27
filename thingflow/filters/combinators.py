# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
This module defines combinators for linq-style functions:
compose, parallel, and passthrough. A linq-style function takes the previous
OutputThing/filter in a chain as its first input ("this"), parameters to the
filter as subsequent inputs, and returns a OutputThing/filter that should be
used as the input to the next step in the filter chain.

We use the term "thunk" for the special case where the linq-style function
takes only a single input - the previous OutputThing/filter in the chain.
The Scheduler.schedule_sensor() method and the functions below can accept
thunks in place filters. If a linq-style filter F was defined using
the @filtermethod decorator, then calling the function directly (not as
a method of a OutputThing) returns a thunk.
"""

from thingflow.base import OutputThing, filtermethod, _make_thunk, \
                           _connect_thunk


def compose(*thunks):
    """Given a list of thunks and/or filters, compose them
    in a sequence and return a thunk.
    """
    def apply(this):
        p = this
        for thunk in thunks:
            assert p, \
                "attempted to compose a terminal InputThing/thunk in non-final position"
            p = _connect_thunk(p, thunk)
        return p
    _make_thunk(apply)
    return apply


def parallel(*connectees):
    """Take one or more InputThings/thunks and create a thunk that will
    connect all of them to "this" when evaluated. Note that the entire
    set of InputThings acts as spurs - the original OutputThing is returned
    as the next OutputThing in the chain.
    """
    def apply(this):
        for c in connectees:
            _connect_thunk(this, c)
        return this
    _make_thunk(apply)
    return apply


@filtermethod(OutputThing)
def passthrough(this, spur):
    """We wish to have a spur off a chain of filters. For example, a writer that
    is a InputThing, but does not implement the OutputThing API. Thus, we have no
    way to put it in the middle of a chain. Or, we might want to implement a
    "fork" in the chain of filters, with two parallel downstream chains.
    
    passthrough takes "this", the previous OutputThing in the chain, and "spur",
    either a InputThing, a thunk (a function that takes the OutputThing as its
    single argument), or a plain anonymous function. The spur is connected to
    the OutputThing and then the OutputThing is returned to continue the chain.
    """
    _connect_thunk(this, spur)
    return this

