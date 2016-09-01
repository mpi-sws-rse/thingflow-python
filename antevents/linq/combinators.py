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

from antevents.base import Publisher, filtermethod

# def thunk(fn, *args, **kwargs):
#     """Given a linq-style function and its arguments, deter its
#     execution until we resolve the publisher it will connect it.
#     We return a function, apply(), that takes this publisher and
#     returns the Filter object.
#     """
#     if len(args)==0 and len(kwargs)==0:
#         return fn
#     def apply(this):
#         return fn(this, *args, **kwargs)
#     return apply


def compose(*thunks):
    """Given a list of thunks and/or filters, compose them
    in a sequence and return a thunk.
    """
    def apply(this):
        p = this
        for thunk in thunks:
            if callable(thunk):
                p = thunk(p)
            else:
                p.subscribe(thunk)
                p = thunk
        return p
    return apply



def parallel(*subscribers):
    """Take one or more subscribers/thunks and create a thunk that will
    subscribe all of them to "this" when evaluated.
    """
    def apply(this):
        for s in subscribers:
            if callable(s):
                s(this)
            else:
                this.subscribe(s)
        return this
    return apply


@filtermethod(Publisher)
def passthrough(this, spur):
    """We wish to have a spur off a chain of filters. For example, a writer that
    is a subscriber, but does not implement the publisher API. Thus, we have no
    way to put it in the middle of a chain. Or, we might want to implement a
    "fork" in the chain of filters, with two parallel downstream chains.
    
    passthrough takes "this", the previous publisher in the chain, and "spur",
    either a subscriber or a thunk (a function that takes the publisher as its
    single argument). The spur is subscribed to the publisher and then the
    publisher is returned to continue the chain.
    """
    if callable(spur):
        spur(this)
    else:
        this.subscribe(spur)
    return this

