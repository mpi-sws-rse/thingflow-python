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

In general, a linq-style function takes the previous publisher/filter in a
chain as its first input, parameters to the filter as subsequent inputs, and
returns a publisher/filter that should be used as the input to the next step
in the filter chain. In addition to being methods on Publisher, they can be
used as first class functions. See combinators.py for some tools to facilitate
this.
"""


def filtermethod(base, alias=None):
    """Function decorator that creates a linq-style filter out of the
    specified function. As described in the antevents.linq documentation,
    it should take a Publisher as its first argument (the source of events)
    and return a Publisher (representing the end the filter sequence once
    the filter is included. The returned Publisher is typically an instance
    of antevents.base.Filter.

    The specified function is used in two places:
    1. A method with the specified name is added to the specified class
       (usually the Publisher base class). This is for the fluent O-O API.
    2. A function is created in the local namespace with the suffix _fn,
       for use in the functional API.
       This function does not take the publisher as an argument. Instead,
       it takes the remaining arguments and then returns a function which,
       when passed a publisher, subscribes to it and returns a filter.

    Decorator arguments:
    :param T base: Base class to extend with method
     (usually antevents.base.Publisher)
    :param string alias: an alias for this function or list of aliases
                         (e.g. map for select, etc.).

    :returns: A function that takes the class to be decorated.
    :rtype: func -> func

    This was adapted from the RxPy extensionmethod decorator.
    """
    def inner(func):
        """This function is returned by the outer extensionmethod()

        :param types.FunctionType func: Function to be decorated
        """

        func_names = [func.__name__,]
        if alias:
            aliases = alias if isinstance(alias, list) else [alias]
            func_names += aliases

        def _thunk(*args, **kwargs):
            if len(args)==0 and len(kwargs)==0:
                return func
            def apply(this):
                return func(this, *args, **kwargs)
            apply.__name__ = func.__name__
            return apply
        _thunk.__name__ = func.__name__ + '_fn'
        
        for func_name in func_names:
            setattr(base, func_name, func)
            func.__globals__[func_name + '_fn'] = _thunk
        return func
    return inner


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
