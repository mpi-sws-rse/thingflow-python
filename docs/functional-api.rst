==============
Functional API
==============

Motivation
----------
The primary API that AntEvents provides for filters is a *fluent* API based
on the concept of *method chaining*: each filter method on the ``Publisher``
base class returns the last publisher in the subscription chain. This
result can then be used for subsequent calls. For example, to apply a
filter followed by a map, we might say::

    publisher.filter(lambda evt: evt.val > 300).map(lambda evt:evt.val)

Underneath the covers, the ``filter()`` call returns a ``Filter`` object
(a subclass of ``Publisher``). The ``map()`` method call is then made
against this object.

This approach is convenient when your processing pipeline really is a
straight line. If you have parallel branches, or more complex structures,
you end up having to break it up with assignment statements. For example,
consider the following dataflow, based on the code in
``examples/rpi/lux_sensor_example.py``::

    lux = SensorPub(LuxSensor())
    lux.output()
    lux.csv_writer(os.path.expanduser('~/lux.csv'))
    actions = lux.map(lambda event: event.val > threshold)
    actions.subscribe(GpioPinOut())
    actions.subscribe(lambda v: print('ON' if v else 'OFF'))
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_periodic_on_separate_thread(lux, interval)
    scheduler.run_forever()

In the above code, ``lux`` has three subscribers, and the output of the ``map``
filter has two subscribers.

Functional API
--------------
To simplfy these cases, we provide a *functional* API that can be used in
place of (or along with) the *fluent* API. For each method added to the
publisher via the ``@filtermethod`` decorator (in ``antevents.base``), a
function with the same name is added to the module containing the definition
(e.g. ``antevents.linq.output`` has an ``output`` function and
``antevents.linq.select`` has ``map`` and ``select`` functions). These functions
take all the parameters of the associated method call (except for the implied
``self`` parameter of a bound method) and return what we call a *thunk*.
A thunk returns a fuction, which when passed a publisher, subscribes to the 


1. As the parameter to a publisher's ``subscribe()`` method.
2. The ``Schedule`` class has ``schedule_sensor()`` and
   ``schedule_sensor_on_separate_thread()`` methods. These take a
   sensor, wrap it in a ``SensorPub`` instance, and then subscribe a sequence
   of filters to the publisher. Each filter can be passed in directly or
   passed indirectly via one of the functional API calls.
3. The module ``antevents.linq.combinators`` defines several functions that
   can be used to combine publishers and functila
