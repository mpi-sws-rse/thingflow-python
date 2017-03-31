.. _output_things:

3. Implementing an OutputThing
==============================
In most cases, one can simply wrap a sensor in the ``SensorAsOutputThing``
class and not worry about the details of how to implement output things. There
are also several pre-defined *readers* under ``thingflow.adapters`` that can
obtain events from external sources like message brokers, flat files, and
databases.

The most likly reason for implmenting a new OutputThing is that you want to
create a new adapter type that does not exist in the standard ThingFlow
library. We will walk through the details in this document.

Subclassing
-----------
When implmenting an output thing, one subclasses from
``thingflow.base.OutputThing``. To emit a new event, the subclass calls the
``_dispatch_next`` method with the event and port name. To signal an error or
completion of the event stream,
one calls ``_dispatch_error`` or ``_dispatch_completed``, respectively. The
base class implementation of these methods are responsible for calling the
``on_next``, ``on_error``, and ``on_completed`` methods for each of the
connected things.

The code to call these ``_dispatch`` methods goes into a well-known method to be
called by the scheduler. The specific method depends how the output thing will
interact with the scheduler. There are two
cases supported by ThingFlow and three associated mixin-classes that define
the methods:

1. ``DirectOutputThingMixin`` defines an ``_observe`` method that can be called
   directly by the scheduler either in the main thread (via
   ``Scheduler.schedule_period()`` or ``Scheduler.schedule_recurring()``) or
   in a separate thread (via
   ``Scheduler.schedule_periodic_on_separate_thread()``).
2. ``EventLoopOutputThingMixin`` is used for an output thing that has its own separate
   event loop. This is run in a separate thread and the connected input things
   are called in the main thread.


Simple CSV Reader
-----------------
OK, with all that out of the way, let us define a simple OutputThing. We will
create a simple CSV-formatted spreadsheet file reader. Each row in the
file corresponds to an event. Here is the class definition (found in
``examples/simple_csv_reader.py``):

.. code-block:: python

    import csv
    from thingflow.base import OutputThing, DirectOutputThingMixin,\
                               SensorEvent, FatalError
    
    class SimpleCsvReader(OutputThing, DirectOutputThingMixin):
        def __init__(self, filename, has_header_row=True):
            super().__init__() # Make sure the output_thing class is initialized
            self.filename = filename
            self.file = open(filename, 'r', newline='')
            self.reader = csv.reader(self.file)
            if has_header_row:
                # swallow up the header row so it is not passed as data
                try:
                    self.reader.__next__()
                except Exception as e:
                    raise FatalError("Problem reading header row of csv file %s: %s" %
                                     (filename, e))
            
        def _observe(self):
            try:
                row = self.reader.__next__()
                event = SensorEvent(ts=float(row[0]), sensor_id=row[1],
                                    val=float(row[2]))
                self._dispatch_next(event)
            except StopIteration:
                self.file.close()
                self._dispatch_completed()
            except FatalError:
                self._close()
                raise
            except Exception as e:
                self.file.close()
                self._dispatch_error(e)
    
The ``SimpleCsvReader`` class subclasses from both ``OutputThing`` and
``DirectOutputThingMixin``. Subclassing from ``OutputThing`` provides the
machinery needed to register connections and propagate events to downstream
input things. ``DirectOutputThingMixin`` defines an empty ``_observe()`` method and
indicates that the scheduler should call ``_observe()`` to dispatch events
whenever the reader has been scheduled.

In the ``__init__()`` constructor, we first make sure that the base class
infrastructure is initialized through ``super().__init__()``. Next, we
open the file, set up the csv reader, and read the header (if needed).

The main action is happening in ``_observe()``. When scheduled, it reads
the next row from the csv file and creates a ``SensorEvent`` from it.
This event is passed on to the output port's connections via
``_dispatch_next()``. If
the end of the file has been reached (indicated by the ``StopIteration``
exception), we instead call ``_dispatch_completed()``. There are two
error cases:

1. If a ``FatalError`` exception is thrown, we close our connection and
   propagate the error up. This will lead to an early termination of
   the event loop.
2. If any other exception is thrown, we pass it downstream via
   ``_dispatch_error()``. It will also close the event stream and
   cause the ``SimpleCsvReader`` to be de-scheduled. The main event
   loop may continue, assuming that there are other scheduled objects.

   
We could save some work in implementing our reader by subclassing from
``thingflow.adapters.generic.DirectReader``. It provides the dispatch
behavior common to most readers.

Reading a File
~~~~~~~~~~~~~~
Now, let us create a simple data file ``test.csv``::

    ts,id,value
    1,1,2
    2,1,3
    3,1,455
    4,1,55

We can instantiate a ``SimpleCsvReader`` to read in the file via::

    reader = SimpleCsvReader("test.csv")

Now, let's hook it to an printing input thing and then run it in the event
loop:

.. code-block:: python

    import asyncio
    from thingflow.base import Scheduler
    import thingflow.adapters.output # load the output method
    
    reader.output()
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_recurring(reader)
    scheduler.run_forever()

We use ``schedule_recurring()`` instead of ``schedule_periodic()``, as we
expect all the data to be already present in the file. There is no sense in
taking periodic samples.

The output looks as follows::

    SensorEvent(sensor_id='1', ts=1.0, val=2.0)
    SensorEvent(sensor_id='1', ts=2.0, val=3.0)
    SensorEvent(sensor_id='1', ts=3.0, val=455.0)
    SensorEvent(sensor_id='1', ts=4.0, val=55.0)
    No more active schedules, will exit event loop

Note that the event loop terminates on its own. This is due to the call to
``_dispatch_completed()`` when the csv reader throws ``StopIteration``.


Output Things with Private Event Loops
--------------------------------------
There can be cases when the underlying API to be called by the OutputThing
requires its own event loop / event listener. To handle this situation,
use the interface provided by ``EventLoopOutputThingMixin``. Your main
event loop for the output ting is implemented in the ``_observe_event_loop()``.
If you call the scheduler's ``schedule_on_private_event_loop()`` method, it
will run this method in a separate thread and then dispatch any events to
the scheduler's main event loop (running in the main thread).

To see some example code demonstrating an output thing using a private event
loop, see ``thingflow.adapters.mqtt.MQTTReader``.
