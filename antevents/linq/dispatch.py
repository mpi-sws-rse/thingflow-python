# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.

from antevents.base import Publisher, DefaultSubscriber, filtermethod


class Dispatcher(Publisher, DefaultSubscriber):
    """Dispatch rules are a list of (predicate, topic) pairs. See the
    documentation on the dispatch() extension method for details.
    """
    def __init__(self, previous_in_chain, dispatch_rules):
        topics = [topic for (pred, topic) in dispatch_rules] + ['default']
        super().__init__(topics=topics)
        self.dispatch_rules = dispatch_rules
        self.dispose = previous_in_chain.subscribe(self)

    def on_next(self, x):
        for (pred, topic) in self.dispatch_rules:
            if pred(x):
                self._dispatch_next(x, topic=topic)
                return
        self._dispatch_next(x, topic='default') # fallthrough case

    def on_completed(self):
        for (pred, topic) in self.dispatch_rules:
            self._dispatch_completed(topic=topic)
        self._dispatch_completed(topic='default')

    def on_error(self, e):
        for (pred, topic) in self.dispatch_rules:
            self._dispatch_error(e, topic=topic)
        self._dispatch_error(e, topic='default')

    def __str__(self):
        return 'dispatch'

@filtermethod(Publisher)
def dispatch(this, dispatch_rules):
    """Dispatch each incoming event to one output topic, according to
    the dispatch rules. The rules are a list of (predicate, topic) pairs.
    The event is dispatched to the first topic where the associated predicate
    returns True. If no predicates return True, the event is dispatched
    to the default topic.
    """
    return Dispatcher(this, dispatch_rules)
    

                  
