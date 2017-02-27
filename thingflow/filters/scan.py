# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from thingflow.base import OutputThing, filtermethod

@filtermethod(OutputThing, alias="aggregate")
def reduce(self, accumulator, seed=None):
    """Applies an accumulator function over a sequence,
    returning the result of the aggregation as a single element in the
    result sequence. The specified seed value is used as the initial
    accumulator value.
    Example:
    1 - res = source.reduce(lambda acc, x: acc + x)
    2 - res = source.reduce(lambda acc, x: acc + x, 0)
    Keyword arguments:
    :param accumulator: An accumulator function to be
        invoked on each element.
    :param seed: Optional initial accumulator value.
    :returns: An observable sequence containing a single element with the
        final accumulator value.
    """

    return self.scan(accumulator, seed=seed).last()

@filtermethod(OutputThing)
def scan(this, accumulator, seed=None):
    """Applies an accumulator function over an observable sequence and
    returns each intermediate result. The optional seed value is used as
    the initial accumulator value. 
    For aggregation behavior with no intermediate results, see OutputThing.aggregate.
    1 - scanned = source.scan(lambda acc, x: acc + x)
    2 - scanned = source.scan(lambda acc, x: acc + x, 0)
    Keyword arguments:
    accumulator -- An accumulator function to be invoked on each element.
    seed -- [Optional] The initial accumulator value.
    Returns an observable sequence containing the accumulated values.
    """

    has_seed = False
    if seed is not None:
        has_seed = True
    has_accumulation = [False]
    accumulation = [None]

    def calculate(x):
        if has_accumulation[0]:
            accumulation[0] = accumulator(accumulation[0], x)
        else:
            accumulation[0] =  accumulator(seed, x) if has_seed else x
            has_accumulation[0] = True
        return accumulation[0]

    return this.map(calculate)
