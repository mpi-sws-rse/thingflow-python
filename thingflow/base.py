# Copyright 2016,2017 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
Base functionality for ThingFlow. All the core abstractions
are defined here. Everything else is just subclassing or using
these abstractions.

The key abstractions are:

 * Thing       - a unit of computation in the data flow graph. Things can be
                 Filters (with inputs and outputs) or Adapters (with only inputs
                 or only outputs).
 * OutputThing - Base class and interface for things that emit event streams on
                 output ports.
 * Sensor      - an object that is (indirectly) connected to the physical world.
                 It can provide its current value through a sample() method.
                 Sensors can be turned into Things by wrapping them with
                 the SensorAsInputThing class.
 * InputThing  - interface for things that receive a stream of events on one or
                 more input ports.
 * Filter      - a thing that is both an InputThing and an OutputThing, with one
                 input and one output. Filters transform data streams.
 * Scheduler   - The scheduler wraps an event loop. It provides periodic and
                 one-time scheduling of OutputThings that originate events.
 * event       - ThingFlow largely does not care about the particulars of the
                 events it processes. However, we define a generic SensorEvent
                 datatype that can be used when the details of the event matter
                 to a thing.

See the README.rst file for more details.
"""

from collections import namedtuple
import threading
import time
import queue
import traceback as tb
import logging
logger = logging.getLogger(__name__)

from thingflow.internal import noop


class InputThing:
    """This is the interface for the default input
    port of a Thing. Other (named) input ports will
    define similar methods with the names as
    on_PORT_next(), on_PORT_error(), and
    on_PORT_completed().
    """
    def on_next(self, x):
        pass
        
    def on_error(self, e):
        pass
        
    def on_completed(self):
        pass


def _on_next_name(port):
    if port==None or port=='default':
        return 'on_next'
    else:
        return 'on_%s_next' % port

def _on_error_name(port):
    if port==None or port=='default':
        return 'on_error'
    else:
        return 'on_%s_error' % port


def _on_completed_name(port):
    if port==None or port=='default':
        return 'on_completed'
    else:
        return 'on_%s_completed' % port


class CallableAsInputThing:
    """Wrap any callable with the InputThing interface.
    We only pass it the on_next() calls. on_error and on_completed
    can be passed in or default to noops.
    """
    def __init__(self, on_next=None, on_error=None, on_completed=None,
                 port=None):
        setattr(self, _on_next_name(port), on_next or noop)
        if on_error:
            setattr(self, _on_error_name(port), on_error)
        else:
            def default_error(err):
                if isinstance(err, FatalError):
                    raise err.with_traceback(err.__traceback__)
                else:
                    logger.error("%s: Received on_error(%s)" %
                                 (self, err))
            setattr(self, _on_error_name(port), default_error)
        setattr(self, _on_completed_name(port), on_completed or noop)
        
    def __str__(self):
        return 'CallableAsInputThing(%s)' % str(self.on_next)

    def __repr__(self):
        return 'CallableAsInputThing(on_next=%s, on_error=%s, on_completed=%s)' % \
            (repr(self.on_next), repr(self.on_error), repr(self.on_completed))


class FatalError(Exception):
    """This is the base class for exceptions that should terminate the event
    loop. This should be for out-of-bound errors, not for normal errors in
    the data stream. Examples of out-of-bound errors include an exception
    in the infrastructure or an error in configuring or dispatching an event
    stream (e.g. publishing to a non-existant port).
    """
    pass

class InvalidPortError(FatalError):
    pass

class UnknownPortError(FatalError):
    pass

class PortAlreadyClosed(FatalError):
    pass


class ExcInDispatch(FatalError):
    """Dispatching an event should not raise an error, other than a
    fatal error.
    """
    pass

# Internal representation of a connection. The first three fields
# are functions which dispatch to the InputThing. The InputThing and input_port
# fields are not needed at runtime, but helpful in debugging.
# We use a class with slots instead of a named tuple because we want to
# change the values of the on_next, etc. functions when tracing (tuples
# are read-only. The attribute access of a named tuple by name is no
# faster than slots. If we need to spead this up at some point, use a
# named tuple but access via the index values (at a cost to readability
# of the code).
class _Connection:
    __slots__ = ('on_next', 'on_completed', 'on_error', 'input_thing',
                 'input_port')
    def __init__(self, on_next, on_completed, on_error, input_thing,
                 input_port):
        self.on_next = on_next
        self.on_completed = on_completed
        self.on_error = on_error
        self.input_thing = input_thing
        self.input_port = input_port

    def __repr__(self):
        return '_Connection(%s,%s,%s,%s,%s)' % \
            (repr(self.on_next), repr(self.on_completed), repr(self.on_error),
             repr(self.input_thing), repr(self.input_port))
    
    def __str__(self):
        return '_Connection(%s,%s)' % \
             (str(self.input_thing), str(self.input_port))

    
class OutputThing:
    """Base class for event generators (output things). The non-underscore
    methods are the public end-user interface. The methods starting with
    underscores are for interactions with the scheduler.
    """
    def __init__(self, ports=None):
        self.__connections__ = {} # map from port to InputThing set
        if ports is None:
            self.__ports__ = set(['default',])
        else:
            self.__ports__ = set(ports)
        for port in self.__ports__:
            self.__connections__[port] = []
        self.__enqueue_fn__ = None
        self.__closed_ports__ = []


    def connect(self, input_thing, port_mapping=None):
        """Connect the InputThing to events on a specific port. The port
        mapping is a tuple of the OutputThing's port name and InputThing's port
        name. It defaults to (default, default).

        This returns a fuction that can be called to remove the connection.
        """
        if port_mapping==None:
            output_port = 'default'
            input_port = 'default'
        else:
            (output_port, input_port) = port_mapping
        if output_port not in self.__ports__:
            raise InvalidPortError("Invalid publish port '%s', valid ports are %s" %
                                    (output_port,
                                     ', '.join([str(s) for s in self.__ports__])))
        if not hasattr(input_thing, _on_next_name(input_port)) and callable(input_thing):
                input_thing = CallableAsInputThing(input_thing, port=input_port)
        try:
            connection = \
                _Connection(on_next=getattr(input_thing, _on_next_name(input_port)),
                              on_completed=getattr(input_thing, _on_completed_name(input_port)),
                              on_error=getattr(input_thing, _on_error_name(input_port)),
                              input_thing=input_thing,
                              input_port=input_port)
        except AttributeError:
            raise InvalidPortError("Invalid input port '%s', missing method(s) on InputThing %s" %
                                    (input_port, input_thing))
        new_connections = self.__connections__[output_port].copy()
        new_connections.append(connection)
        self.__connections__[output_port] = new_connections
        def disconnect():
            # To remove the connection, we replace the entire list with a copy
            # that is missing the connection. This allows disconnect() to be
            # called within a _dispatch method. Otherwise, we get an error if
            # we attempt to change the list of connections while iterating over
            # it.
            new_connections = self.__connections__[output_port].copy()
            #new_connections.remove(connection)
            # we look for a connection to the same port and thing rather than
            # the same object - the object may have changed due to tracing
            found = False
            for c in self.__connections__[output_port]:
                if c.input_thing==input_thing and c.input_port==input_port:
                    new_connections.remove(c)
                    found = True
                    break
            assert found
            self.__connections__[output_port] = new_connections
        return disconnect

    def _has_connections(self):
        """Used by the scheduler to see the thing has any more outgoing connections.
        If a scheduled thing no longer has output connections, it is descheduled.
        """
        for (port, conns) in self.__connections__.items():
            if len(conns)>0:
                return True
        return False
    
    def _schedule(self, enqueue_fn):
        """This method is used by the scheduler to specify an enqueue function
        to be called
        when dispatching events to the connections. This is used when the
        OutputThing runs in a separate thread from the main event loop. If
        that is not the case, the enqueue function should be None.
        """
        self.__enqueue_fn__ = enqueue_fn

    def _close_port(self, port):
        """Port will receive no more messages. Remove the port from
        this OutputThing.
        """
        #print("Closing port %s on %s" % (port, self)) # XXX
        del self.__connections__[port]
        self.__ports__.remove(port)
        self.__closed_ports__.append(port)

    def _dispatch_next(self, x, port=None):
        #print("Dispatch next called on %s, port %s, msg %s" % (self, port, str(x)))
        if port==None:
            port = 'default'
        try:
            connections = self.__connections__[port]
        except KeyError as e:
            if port in self.__closed_ports__:
                raise PortAlreadyClosed("Port '%s' on OutputThing %s already had an on_completed or on_error_event" %
                                         (port, self))
            else:
                raise UnknownPortError("Unknown port '%s' in OutputThing %s" %
                                        (port, self)) from e
        if len(connections) == 0:
            return
        enq = self.__enqueue_fn__
        if enq:
            for s in connections:
                enq(s.on_next, x)
        else:
            try:
                for s in connections:
                    s.on_next(x)
            except FatalError:
                raise
            except Exception as e:
                raise ExcInDispatch("Unexpected exception when dispatching event '%s' to InputThing %s from OutputThing %s" %
                                    (repr(x), s.input_thing, self)) from e

    def _dispatch_completed(self, port=None):
        if port==None:
            port = 'default'
        try:
            connections = self.__connections__[port]
        except KeyError as e:
            if port in self.__closed_ports__:
                raise PortAlreadyClosed("Port '%s' on OutputThing %s already had an on_completed or on_error_event" %
                                         (port, self))
            else:
                raise UnknownPortError("Unknown port '%s' in OutputThing %s" % (port, self)) from e
        enq = self.__enqueue_fn__
        if enq:
            for s in connections:
                enq(s.on_completed)
        else:
            try:
                for s in connections:
                    s.on_completed()
            except FatalError:
                raise
            except Exception as e:
                raise ExcInDispatch("Unexpected exception when dispatching completed to InputThing %s from OutputThing %s" %
                                    (s.input_thing, self)) from e
        self._close_port(port)

    def _dispatch_error(self, e, port=None):
        if port==None:
            port = 'default'
        try:
            connections = self.__connections__[port]
        except KeyError as e:
            if port in self.__closed_ports__:
                raise PortAlreadyClosed("Port '%s' on OutputThing %s already had an on_completed or on_error_event" %
                                         (port, self))
            else:
                raise UnknownPortError("Unknown port '%s' in OutputThing %s" % (port, self)) from e
        enq = self.__enqueue_fn__
        if enq:
            for s in connections:
                enq(s.on_error, e)
        else:
            try:
                for s in connections:
                    s.on_error(e)
            except FatalError:
                raise
            except Exception as e:
                raise ExcInDispatch("Unexpected exception when dispatching error '%s' to InputThing %s from OutputThing %s" %
                                    (repr(e), s.input_thing, self)) from e
        self._close_port(port)

    def print_downstream(self):
        """Recursively print all the downstream paths. This is for debugging.
        """
        def has_connections(thing):
            if not hasattr(thing, '__connections__'):
                return False
            return thing._has_connections()
        def print_from(current_seq, thing):
            if has_connections(thing):
                for (port, connections) in thing.__connections__.items():
                    for connection in connections:
                        if port=='default' and \
                           connection.input_port=='default':
                            next_seq = " => %s" % connection.input_thing
                        else:
                            next_seq = " [%s]=>[%s] %s" % \
                                        (port, connection.input_port,
                                         connection.input_thing)
                        print_from(current_seq + next_seq,
                                   connection.input_thing)
            else:
                print(current_seq)
        print("***** Dump of all paths from %s *****" % self.__str__())
        print_from("  " + self.__str__(), self)
        print("*"*(12+len(self.__str__())))

    def trace_downstream(self):
        """Install wrappers that print a trace message for each
        event on this thing and all downsteam things.
        """
        def has_connections(thing):
            if not hasattr(thing, '__connections__'):
                return False
            return thing._has_connections()
        def fmt(thing, port):
            return '%s.%s' % (str(thing), port) if port!='default' \
                else str(thing)
        def trace_on_next(thing, output_port, connection, x):
            print("  %s => (%s) => %s" %
                  (fmt(thing, output_port), str(x),
                   fmt(connection.input_thing,
                       connection.input_port)))
            connection.on_next(x)
        def trace_on_error(thing, output_port, connection, error):
            print("  %s => on_error(%s) => %s" %
                  (fmt(thing, output_port), str(error),
                   fmt(connection.input_thing,
                   connection.input_port)))
            connection.on_error(error)
        def trace_on_completed(thing, output_port, connection):
            print("  %s => on_completed => %s" %
                  (fmt(thing, output_port),
                   fmt(connection.input_thing,
                       connection.input_port)))
            connection.on_completed()
            
        def make_trace_connection(src_thing, output_port, old_connection):
            return _Connection(
                on_next=lambda x: trace_on_next(src_thing, output_port,
                                                old_connection, x),
                on_error=lambda e: trace_on_error(src_thing, output_port,
                                                  old_connection, e),
                on_completed=lambda : trace_on_completed(src_thing,
                                                         output_port,
                                                         old_connection),
                input_thing=old_connection.input_thing,
                input_port=old_connection.input_port)
        def trace_from(thing):
            if has_connections(thing):
                new_connections = {}
                for (port, connections) in thing.__connections__.items():
                    connections_for_port = []
                    for connection in connections:
                        trace_from(connection.input_thing)
                        connections_for_port.append(make_trace_connection(thing,
                                                                          port,
                                                                          connection))
                    new_connections[port] = connections_for_port
                thing.__connections__ = new_connections
        trace_from(self)
        print("***** installed tracing in all paths starting from %s" %
              str(self))
        
    def pp_connections(self):
        """pretty print the set of connections"""
        h1 = "***** InputThings for %s *****" % self
        print(h1)
        for port in sorted(self.__connections__.keys()):
            print("  Port %s" % port)
            for s in self.__connections__[port]:
                print("    [%s] => %s" % (s.input_port, s.input_thing))
                print("      on_next: %s" % s.on_next)
                print("      on_completed: %s" % s.on_completed)
                print("      on_error: %s" % s.on_error)
        print("*"*len(h1))

    def __str__(self):
        return  self.__class__.__name__ + '()'
                

class Filter(OutputThing, InputThing):
    """A filter has a default input port and a default output port. It is
    used for data transformations. The default implementations of on_next(),
    on_completed(), and on_error() just pass the event on to the downstream
    connection.
    """
    def __init__(self, previous_in_chain):
        super().__init__()
        # connect to the previous filter
        self.disconnect_from_upstream = previous_in_chain.connect(self)

    def on_next(self, x):
        self._dispatch_next(x)

    def on_error(self, e):
        self._dispatch_error(e)

    def on_completed(self):
        self._dispatch_completed()

    def __str__(self):
        return self.__class__.__name__ + '()'

        
class XformOrDropFilter(Filter):
    """Implements a slightly more complex filter protocol where events may be
    transformed or dropped. Subclasses just need to implement the _filter() and
    _complete() methods.
    """
    def __init__(self, previous_in_chain):
        super().__init__(previous_in_chain)

    def on_next(self, x):
        """Calls _filter(x) to process
        the event. If _filter() returns None, nothing futher is done. Otherwise,
        the return value is passed to the downstream connection. This allows you
        to both transform as well as send only selected events.

        Errors other than FatalError are handled gracefully by calling
        self.on_error() and then disconnecing from the upstream OutputThing.
        """
        try:
            x_prime = self._filter(x)
        except FatalError:
            raise
        except Exception as e:
            logger.exception("Got an exception on %s._filter(%s)" %
                             (self, x))
            self.on_error(e)
            self.disconnect_from_upstream()
        else:
            if x_prime is not None:
                self._dispatch_next(x_prime)

    def _filter(self, x):
        """Filtering method to be implemented by subclasses.
        """
        return x

    def _complete(self):
        """Method to be overridden by subclasses. It is called as a part of
        on_error() and on_completed() to give a chance to pass down a held-back
        event. Return None if there is no such event.

        You can also clean up any state in this method (e.g. close connections).

        Shold not throw any exceptions other than FatalError.
        """
        return None
    
    def on_error(self, e):
        """Passes on any final event and then passes the notification to the
        next Thing.
        If you need to clean up any state, do it in _complete().
        """
        x = self._complete()
        if x is not None:
            self._dispatch_next(x)
        self._dispatch_error(e)

    def on_completed(self):
        """Passes on any final event and then passes the notification to the
        next Thing.
        If you need to clean up any state, do it in _complete().
        """
        x = self._complete()
        if x is not None:
            self._dispatch_next(x)
        self._dispatch_completed()


class FunctionFilter(Filter):
    """Implement a filter by providing functions that implement the
    on_next, on_completed, and one_error logic. This is useful
    when the logic is really simple or when a more functional programming
    style is more convenient.

    Each function takes a "self" parameter, so it works almost like it was
    defined as a bound method. The signatures are then::

        on_next(self, x)
        on_completed(self)
        on_error(self, e)

    If a function is not provided to __init__, we just dispatch the call downstream.
    """
    def __init__(self, previous_in_chain,
                 on_next=None, on_completed=None,
                 on_error=None, name=None):
        """name is an option name to be used in __str__() calls.
        """
        super().__init__(previous_in_chain)
        self._on_next = on_next
        self._on_error = on_error
        self._on_completed = on_completed
        if name:
            self.name = name

    def on_next(self, x):
        try:
            if self._on_next:
                # we pass in an extra "self" since this is a function, not a method
                self._on_next(self, x)
            else:
                self._dispatch_next(x)
        except FatalError:
            raise
        except Exception as e:
            logger.exception("Got an exception on %s.on_next(%s)" %
                             (self, x))
            self.on_error(e)
            self.disconnect_from_upstream() # stop from getting upstream events

    def on_error(self, e):
        if self._on_error:
            self._on_error(self, e)
        else:
            self._dispatch_error(e)
        
    def on_completed(self):
        if self._on_completed:
            self._on_completed(self)
        else:
            self._dispatch_completed()

    def __str__(self):
        if hasattr(self, 'name'):
            return self.name
        else:
            return self.__class__.__name__ + '()'


def _is_thunk(t):
    return hasattr(t, '__thunk__')

def _make_thunk(t):
    setattr(t, '__thunk__', True)

class _ThunkBuilder:
    """This is used to create a thunk from a linq-style
    method.
    """
    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__

    def __call__(self, *args, **kwargs):
        if len(args)==0 and len(kwargs)==0:
            _make_thunk(self.func)
            return self.func
        def apply(this):
            return self.func(this, *args, **kwargs)
        apply.__name__ = self.__name__
        _make_thunk(apply)
        return apply
    def __repr__(self):
        return "_ThunkBuilder(%s)" % self.__name__

def _connect_thunk(prev, thunk):
    """Connect the thunk to the previous in the chain. Handles
    all the cases where we might be given a filter, a thunk,
    a thunk builder (unevaluated linq function), or a bare callable."""
    if callable(thunk):
        if _is_thunk(thunk):
            return thunk(prev)
        elif isinstance(thunk, _ThunkBuilder):
            real_thunk = thunk()
            assert _is_thunk(real_thunk)
            return real_thunk(prev)
        else: # bare callable, will be wrapped by the connect() method
            prev.connect(thunk)
            return None
    else:
        return prev.connect(thunk) # assumed to be a filter
    

def filtermethod(base, alias=None):
    """Function decorator that creates a linq-style filter out of the
    specified function. As described in the thingflow.linq documentation,
    it should take a OutputThing as its first argument (the source of events)
    and return a OutputThing (representing the end the filter sequence once
    the filter is included. The returned OutputThing is typically an instance
    of thingflow.base.Filter.

    The specified function is used in two places:

    1. A method with the specified name is added to the specified class
       (usually the OutputThing base class). This is for the fluent (method
       chaining) API.
    2. A function is created in the local namespace for use in the functional API.
       This function does not take the OutputThing as an argument. Instead,
       it takes the remaining arguments and then returns a function which,
       when passed a OutputThing, connects to it and returns a filter.

    Decorator arguments:

    * param T base: Base class to extend with method
      (usually thingflow.base.OutputThing)
    * param string alias: an alias for this function or list of aliases
                         (e.g. map for select, etc.).
    * returns: A function that takes the class to be decorated.
    * rtype: func -> func

    This was adapted from the RxPy extensionmethod decorator.
    """
    def inner(func):
        """This function is returned by the outer filtermethod()

        :param types.FunctionType func: Function to be decorated
        """

        func_names = [func.__name__,]
        if alias:
            aliases = alias if isinstance(alias, list) else [alias]
            func_names += aliases

        _thunk = _ThunkBuilder(func)

        # For the primary name and all aliases, set the name on the
        # base class as well as in the local namespace.
        for func_name in func_names:
            setattr(base, func_name, func)
            func.__globals__[func_name] = _thunk
        return _thunk
    return inner


class DirectOutputThingMixin:
    """This is the interface for OutputThings that should be directly
    scheduled by the scheduler (e.g. through schedule_recurring(),
    schedule_periodic(), or schedule_periodic_on_separate_thread).
    """
    def _observe(self):
        """Get an event and call the appropriate dispatch function.
        """
        raise NotImplemented
    

class EventLoopOutputThingMixin:
    """OutputThing that gets messages from an event loop, either the same
    loop as the scheduler or a separate one.
    """
    def _observe_event_loop(self):
        """Call the event OutputThing's event loop. When
        an event occurs, the appropriate _dispatch method should
        be called.
        """
        raise NotImplemented

    def _stop_loop(self):
        """When this method is called, the OutputThing should exit the
        event loop as soon as possible.
        """
        raise NotImplemented


class IterableAsOutputThing(OutputThing, DirectOutputThingMixin):
    """Convert any interable to an OutputThing. This can be
    used with the schedule_recurring() and schedule_periodic()
    methods of the scheduler.
    """
    def __init__(self, iterable, name=None):
        super().__init__()
        self.iterable = iterable
        self.name = name
    
    def _observe(self):
        try:
            event = self.iterable.__next__()
        except StopIteration:
            self._close()
            self._dispatch_completed()
        except FatalError:
            self._close()
            raise
        except Exception as e:
            # If the iterable throws an exception, we treat it as non-fatal.
            # The error is dispatched downstream and the connection closed.
            # If other sensors are running, things will continue.
            tb.print_exc()
            self._close()
            self._dispatch_error(e)
        else:
            self._dispatch_next(event)

    def _close(self):
        """This method is called when we stop the iteration, either due to
        reaching the end of the sequence or an error. It can be overridden by
        subclasses to clean up any state and release resources (e.g. closing
        open files/connections).
        """
        pass
    
    def __str__(self):
        if hasattr(self, 'name') and self.name:
            return self.name
        else:
            return super().__str__()
           
def from_iterable(i):
    return IterableAsOutputThing(i)

def from_list(l):
    return IterableAsOutputThing(iter(l))

# XXX Move this out of base.py
class FunctionIteratorAsOutputThing(OutputThing, DirectOutputThingMixin):
    """Generates an OutputThing sequence by running a state-driven loop
       producing the sequence's elements. Example::

           res = GenerateOutputThing(0,
                                     lambda x: x < 10,
                                     lambda x: x + 1,
                                     lambda x: x)

        initial_state: Initial state.
        condition: Condition to terminate generation (upon returning False).
        iterate: Iteration step function.
        result_selector: Selector function for results produced in the sequence.

        Returns the generated sequence.
    """

    def __init__(self, initial_state, condition, iterate, result_selector):
        super().__init__()
        self.value = initial_state
        self.condition = condition
        self.iterate = iterate
        self.result_selector = result_selector 
        self.first = True

    def _observe(self):
        try:
            if self.first: # first time: just send the value
                self.first = False
                if self.condition(self.value):
                    r = self.result_selector(self.value)
                    self._dispatch_next(r)
                else:
                    self._dispatch_completed()
            else:
                if self.condition(self.value):
                    self.value = self.iterate(self.value)
                    r = self.result_selector(self.value)
                    self._dispatch_next(r)
                else: 
                    self._dispatch_completed()
        except Exception as e:
            self._dispatch_error(e)

def from_func(init, cond, iter, selector):
    return FunctionIteratorAsOutputThing(init, cond, iter, selector)



# Define a default sensor event as a tuple of sensor id, timestamp, and value.
SensorEvent = namedtuple('SensorEvent', ['sensor_id', 'ts', 'val'])

def make_sensor_event(sensor, sample):
    """Given a sensor object and a sample taken from that sensor,
    return a SensorEvent tuple."""
    return SensorEvent(sensor_id=sensor.sensor_id, ts=time.time(),
                       val=sample)


class SensorAsOutputThing(OutputThing, DirectOutputThingMixin):
    """OutputThing that samples a sensor upon its observe call, creates
    an event from the sample, and dispatches it forward. A sensor is just
    an object that has a sensor_id property and a sample() method. If the
    sensor wants to complete the stream, it should throw a StopIteration
    exception.

    By default, it generates SensorEvent instances. This behavior can be
    changed by passing in a different function for make_event_fn.
    """
    def __init__(self, sensor, make_event_fn=make_sensor_event):
        super().__init__()
        self.sensor = sensor
        self.make_event_fn = make_event_fn
        
    def _observe(self):
        try:
            self._dispatch_next(self.make_event_fn(self.sensor,
                                                   self.sensor.sample()))
        except FatalError:
            raise
        except StopIteration:
            self._dispatch_completed()
        except Exception as e:
            self._dispatch_error(e)
    
    def __repr__(self):
        return 'SensorAsOutputThing(%s)' % repr(self.sensor)


class BlockingInputThing:
    """This implements a InputThing which may potential block when sending an
    event outside the system. The InputThing is run on a separate thread. We
    create proxy methods for each port that can be called directly - these
    methods just queue up the call to run in the worker thread. 

    The actual implementation of the InputThing goes in the _on_next,
    _on_completed, and _on_error methods. Note that we don't dispatch to separate
    methods for each port. This is because the port is likely to end up as
    just a message field rather than as a separate destination in the lower
    layers.
    """
    def __init__(self, scheduler, ports=None):
        if ports==None:
            self.ports = ['default',]
        else:
            self.ports = ports
        self.num_closed_ports = 0
        # create local proxy methods for each port
        for port in self.ports:
            setattr(self, _on_next_name(port),
                    lambda x: self.__queue__.put((self._on_next, False,
                                                     [port, x]),))
            setattr(self, _on_completed_name(port),
                    lambda: self.__queue__.put((self._on_completed, True,
                                                [port]),))
            setattr(self, _on_error_name(port),
                    lambda e: self.__queue__.put((self._on_error, True,
                                                  [port, e]),))
        self.__queue__ = queue.Queue()
        self.scheduler = scheduler
        self.thread = _ThreadForBlockingInputThing(self, scheduler)
        self.scheduler.active_schedules[self] = self.request_stop
        def start():
            self.thread.start()
        self.scheduler.event_loop.call_soon(start)

    def request_stop(self):
        """This can be called to stop the thread before it is automatically
        stopped when all ports are closed. The close() method will be
        called and the InputThing cannot be restarted later.
        """
        if self.thread==None:
            return # no thread to stop
        self.__queue__.put(None) # special stop token

    def _wait_and_dispatch(self):
        """Called by main loop of blocking thread to block for a request
        and then dispatch it. Returns True if it processed a normal request
        and False if it got a stop message or there is no more events possible.
        """
        action = self.__queue__.get()
        if action is not None:
            (method, closing_port, args) = action
            method(*args)
            if closing_port:
                self.num_closed_ports += 1
                if self.num_closed_ports==len(self.ports):
                    # no more ports can receive events, treat this
                    # as a stop.
                    print("Stopping blocking InputThing %s" % self)
                    return False
            return True # more work possible
        else:
            return False # stop requested
        
        
    def _on_next(self, port, x):
        """Process the on_next event. Called in blocking thread."""
        pass

    def _on_completed(self, port):
        """Process the on_completed event. Called in blocking thread."""
        pass

    def _on_error(self, port, e):
        """Process the on_error event. Called in blocking thread."""
        pass

    def _close(self):
        """This is called when all ports have been closed. This can be used
        to close any connections, etc.
        """
        pass

    
class _ThreadForBlockingInputThing(threading.Thread):
    """Background thread for a InputThing that passes events to the
    external world and might block.
    """
    def __init__(self, input_thing, scheduler):
        self.input_thing = input_thing
        self.scheduler= scheduler
        self.stop_requested = False
        super().__init__()

    def run(self):
        try:
            more = True
            while more:
                more = self.input_thing._wait_and_dispatch()                
        except Exception as e:
            msg = "_wait_and_dispatch for %s exited with error: %s" % \
                  (self.input_thing, e)
            logger.exception(msg)
            self.input_thing._close()
            self.input_thing.thread = None # disassociate this thread
            def die(): # need to stop the scheduler in the main loop
                del self.scheduler.active_schedules[self.input_thing]
                raise ScheduleError(msg) from e
            self.scheduler.event_loop.call_soon_threadsafe(die)
        else:
            self.input_thing._close()
            self.input_thing.thread = None # disassociate this thread
            def done():
                self.scheduler._remove_from_active_schedules(self.input_thing)
            self.scheduler.event_loop.call_soon_threadsafe(done)
                


class _ThreadForBlockingOutputThing(threading.Thread):
    """Background thread for OutputThings that might block.
    """
    def __init__(self, output_thing, interval, scheduler):
        self.output_thing = output_thing
        self.interval = interval
        self.scheduler = scheduler
        self.stop_requested = False
        super().__init__()

    def _stop_loop(self):
        self.stop_requested = True

    def run(self):
        def enqueue_fn(fn, *args):
            self.scheduler.event_loop.call_soon_threadsafe(fn, *args)
        self.output_thing._schedule(enqueue_fn=enqueue_fn)
            
        try:
            while True:
                if self.stop_requested:
                    break
                start = time.time()
                self.output_thing._observe()
                if self.output_thing._has_connections():
                    break
                time_left = self.interval - (time.time() - start)
                if time_left > 0 and (not self.stop_requested):
                    time.sleep(time_left)
        except Exception as e:
            msg = "_observe for %s exited with error" % self.output_thing
            logger.exception(msg)
            def die(): # need to stop the scheduler in the main loop
                del self.scheduler.active_schedules[self.output_thing]
                raise ScheduleError(msg) from e
            self.scheduler.event_loop.call_soon_threadsafe(die)
        else:
            def done():
                self.scheduler._remove_from_active_schedules(self.output_thing)
            self.scheduler.event_loop.call_soon_threadsafe(done)
            
            
class ScheduleError(FatalError):
    pass


class Scheduler:
    """Wrap an asyncio event loop and provide methods for various kinds of
    periodic scheduling.
    """
    def __init__(self, event_loop):
        self.event_loop = event_loop
        self.active_schedules = {} # mapping from task to schedule handle
        self.pending_futures = {}
        self.next_future_id = 1
        # Set the following to an exception if we are exiting the loop due to
        # an exception. We will then raise a SchedulerError when the event loop
        # exits.
        self.fatal_error = None
        # we set the exception handler to stop all active schedules and
        # break out of the event loop if we get an unexpected error.
        def exception_handler(loop, context):
            assert loop==self.event_loop
            self.fatal_error = context['exception']
            self.stop()
        self.event_loop.set_exception_handler(exception_handler)

    def _remove_from_active_schedules(self, output_thing):
        """Remove the specified OutputThing from the active_schedules map.
        If there are no more active schedules, we will request exiting of
        the event loop. This method must be run from the main thread.
        """
        del self.active_schedules[output_thing]
        if len(self.active_schedules)==0:
            print("No more active schedules, will exit event loop")
            self.stop()

    def schedule_periodic(self, output_thing, interval):
        """Returns a callable that can be used to remove the OutputThing from the
        scheduler.
        """
        def cancel():
            try:
                handle = self.active_schedules[output_thing]
            except KeyError:
                raise ScheduleError("Attempt to de-schedule OutputThing %s, which does not have an active schedule" %
                                    output_thing)
            handle.cancel()
            self._remove_from_active_schedules(output_thing)
        def run():
            assert output_thing in self.active_schedules
            output_thing._observe()
            more = output_thing._has_connections()
            if not more and output_thing in self.active_schedules:
                self._remove_from_active_schedules(output_thing)
            elif output_thing in self.active_schedules:
                handle = self.event_loop.call_later(interval, run)
                self.active_schedules[output_thing] = handle
                output_thing._schedule(enqueue_fn=None)
        handle = self.event_loop.call_later(interval, run)
        self.active_schedules[output_thing] = handle
        output_thing._schedule(enqueue_fn=None)
        return cancel

    def schedule_sensor(self, sensor, interval, *input_thing_sequence,
                        make_event_fn=make_sensor_event,
                        print_downstream=False):
        """Create a OutputThing wrapper for the sensor and schedule it at the
        specified interval. Compose the specified connections (and/or thunks)
        into a sequence and connect the sequence to the sensor's OutputThing.
        Returns a thunk that can be used to remove the OutputThing from the
        scheduler.
        """
        output_thing = SensorAsOutputThing(sensor, make_event_fn=make_event_fn)
        prev = output_thing
        for s in input_thing_sequence:
            assert prev,\
                "attempted to compose a terminal InputThing/thunk in a non-final position"
            prev = _connect_thunk(prev, s)
        if print_downstream:
            output_thing.print_downstream() # just for debugging
        return self.schedule_periodic(output_thing, interval)
    
    def schedule_recurring(self, output_thing):
        """Takes a DirectOutputThingMixin and calls _observe() to get events. If,
        after the call, there are no downstream connections, the scheduler will
        deschedule the output thing.

        This variant is useful for something like an iterable. If the call to get
        the next event would block, don't use this! Instead, one of the calls
        that runs in a separate thread (e.g. schedule_recuring_separate_thread()
        or schedule_periodic_separate_thread()).

        Returns a callable that can be used to remove the OutputThing from the
        scheduler.
        """
        def cancel():
            print("canceling schedule of %s" % output_thing)
            try:
                handle = self.active_schedules[output_thing]
            except KeyError:
                raise ScheduleError("Attempt to de-schedule OutputThing %s, which does not have an active schedule" %
                                    output_thing)
            handle.cancel()
            self._remove_from_active_schedules(output_thing)
        def run():
            assert output_thing in self.active_schedules
            output_thing._observe()
            more = output_thing._has_connections()
            if not more and output_thing in self.active_schedules:
                self._remove_from_active_schedules(output_thing)
            elif output_thing in self.active_schedules:
                handle = self.event_loop.call_soon(run)
                self.active_schedules[output_thing] = handle
                output_thing._schedule(enqueue_fn=None)
        handle = self.event_loop.call_soon(run)
        self.active_schedules[output_thing] = handle
        output_thing._schedule(enqueue_fn=None)
        return cancel

    def schedule_on_main_event_loop(self, output_thing):
        """Schedule an OutputThing that runs on the main event loop.
        The OutputThing is assumed to implement EventLoopOutputThingMixin.
        Returns a callable that can be used to unschedule the OutputThing.
        """
        def stop():
            # tell the OutputThing to stop. When the OutputThing has finished
            # processing any messages, it MUST call
            # _remove_from_active_schedules() on the scheduler.
            output_thing._stop_loop()
        self.active_schedules[output_thing] = stop
        self.event_loop.call_soon(output_thing._observe_event_loop)
        return stop
    
    def schedule_on_private_event_loop(self, output_thing):
        """Schedule an OutputThing that has its own event loop on another thread.
        The OutputThing is assumed to implement EventLoopOutputThingMixin.
        Returns a callable that can be used to unschedule the OutputThing, by
        requesting that the event loop stop.
        """
        def enqueue_fn(fn, *args):
            self.event_loop.call_soon_threadsafe(fn, *args)
        def thread_main():
            try:
                output_thing._schedule(enqueue_fn=enqueue_fn)
                # ok, lets run the event loop
                output_thing._observe_event_loop()
            except Exception as e:
                msg = "Event loop for %s exited with error" % output_thing
                logger.exception(msg)
                def die(): # need to stop the scheduler in the main loop
                    del self.active_schedules[output_thing]
                    raise ScheduleError(msg) from e
                self.event_loop.call_soon_threadsafe(die)
            else:
                def loop_done():
                    self._remove_from_active_schedules(output_thing)
                self.event_loop.call_soon_threadsafe(loop_done)
                    
        t = threading.Thread(target=thread_main)
        self.active_schedules[output_thing] = output_thing._stop_loop
        self.event_loop.call_soon(t.start)
        return output_thing._stop_loop

    def schedule_periodic_on_separate_thread(self, output_thing, interval):
        """Schedule an OutputThing to run in a separate thread. It should
        implement the DirectOutputThingMixin.
        Returns a callable that can be used to unschedule the OutputThing, by
        requesting that the child thread stop.
        """
        t = _ThreadForBlockingOutputThing(output_thing, interval, self)
        self.active_schedules[output_thing] = t._stop_loop
        self.event_loop.call_soon(t.start)
        return t._stop_loop

    def schedule_sensor_on_separate_thread(self, sensor, interval, *input_thing_sequence,
                                           make_event_fn=make_sensor_event):
        """Create a OutputThing wrapper for the sensor and schedule it at the
        specified interval. Compose the specified connections (and/or thunks)
        into a sequence and connect the sequence to the sensor's OutputThing.
        Returns a thunk that can be used to remove the OutputThing from the
        scheduler.
        """
        output_thing = SensorAsOutputThing(sensor, make_event_fn=make_event_fn)
        prev = output_thing
        for s in input_thing_sequence:
            assert prev,\
                "attempted to compose a terminal InputThing/thunk in a non-final position"
            prev = _connect_thunk(prev, s)
        return self.schedule_periodic_on_separate_thread(output_thing, interval)
    
    def schedule_later_one_time(self, output_thing, interval):
        def cancel():
            print("canceling schedule of %s" % output_thing)
            try:
                handle = self.active_schedules[output_thing]
            except KeyError:
                raise ScheduleError("Attempt to de-schedule OutputThing %s, which does not have an active schedule" %
                                    output_thing)
            handle.cancel()
            self._remove_from_active_schedules(output_thing)
        def run():
            assert output_thing in self.active_schedules
            # Remove from the active schedules since this was a one-time schedule.
            # Note that the _observe() call could potentially reschedule the
            # OutputThing through another call to the scheduler.
            self._remove_from_active_schedules(output_thing)
            output_thing._observe()
        handle = self.event_loop.call_later(interval, run)
        self.active_schedules[output_thing] = handle
        output_thing._schedule(enqueue_fn=None)
        return cancel
    
    def run_forever(self):
        """Call the event loop's run_forever(). We don't really run forever:
        the event loop is exited if we run out of scheduled events or if stop()
        is called.
        """
        try:
            self.event_loop.run_forever()
        except KeyboardInterrupt:
            # If someone hit Control-C to break out of the loop,
            # they might be trying to diagonose a hang. Print the
            # active OutputThings here before passing on the interrupt.
            print("Active OutputThings: %s" %
                  ', '.join([('%s'%o) for o in self.active_schedules.keys()]))
            raise
        if self.fatal_error is not None:
            raise ScheduleError("Scheduler aborted due to fatal error") \
                from self.fatal_error

    def _schedule_coroutine(self, coro, done_callback):
        """This is for low-level components that deal directly with
        the event loop to to schedule a coroutine. We
        track them so we can either wait for or cancel them when stop()
        is called.
        """
        fid = self.next_future_id
        future = self.event_loop.create_task(coro)
        # the combined callback. To avoid race conditions, always
        # call the provided done callback before we remove the future.
        def cb(f):
            done_callback(f)
            del self.pending_futures[fid]
        self.pending_futures[fid] = future
        future.add_done_callback(cb)
        self.next_future_id += 1
        return future
        
    def stop(self):
        """Stop any active schedules for output things and then call stop() on
        the event loop.
        """
        for (task, handle) in self.active_schedules.items():
            #print("Stopping %s" % task)
            # The handles are either event scheduler handles (with a cancel
            # method) or just callables to be called directly.
            if hasattr(handle, 'cancel'):
                handle.cancel()
            else:
                handle()
        self.active_schedules = {}
        # go through the pending futures. We don't stop the
        # event loop until all the pending futures have been
        # completed or stopped by their callers.
        for (fid, f) in self.pending_futures.items():
            if f.done() == False:
                # if we still have pending futures, we try the
                # stop again after the first one we see has
                # completed.
                #print("Waiting for future %d (%s)" % (fid, repr(f)))
                def recheck_stop(f):
                    exc = f.exception()
                    if exc:
                        raise FatalError("Exception in coroutine %s" % repr(f)) from exc
                    else:
                        self.stop()
                f.add_done_callback(recheck_stop)
                return
            elif f.exception():
                raise FatalError("Exception in coroutine %s" %  repr(f)) from exc
        self.event_loop.stop()
