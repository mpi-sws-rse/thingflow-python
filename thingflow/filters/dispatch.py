# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.

from thingflow.base import OutputThing, InputThing, filtermethod


class Dispatcher(OutputThing, InputThing):
    """Dispatch rules are a list of (predicate, port) pairs. See the
    documentation on the dispatch() extension method for details.
    """
    def __init__(self, previous_in_chain, dispatch_rules):
        ports = [port for (pred, port) in dispatch_rules] + ['default']
        super().__init__(ports=ports)
        self.dispatch_rules = dispatch_rules
        self.disconnect = previous_in_chain.connect(self)

    def on_next(self, x):
        for (pred, port) in self.dispatch_rules:
            if pred(x):
                self._dispatch_next(x, port=port)
                return
        self._dispatch_next(x, port='default') # fallthrough case

    def on_completed(self):
        for (pred, port) in self.dispatch_rules:
            self._dispatch_completed(port=port)
        self._dispatch_completed(port='default')

    def on_error(self, e):
        for (pred, port) in self.dispatch_rules:
            self._dispatch_error(e, port=port)
        self._dispatch_error(e, port='default')

    def __str__(self):
        return 'dispatch'

@filtermethod(OutputThing)
def dispatch(this, dispatch_rules):
    """Dispatch each incoming event to one output port, according to
    the dispatch rules. The rules are a list of (predicate, port) pairs.
    The event is dispatched to the first port where the associated predicate
    returns True. If no predicates return True, the event is dispatched
    to the default port.
    """
    return Dispatcher(this, dispatch_rules)
    

                  
