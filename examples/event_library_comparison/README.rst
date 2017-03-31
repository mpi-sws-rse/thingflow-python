===========================
Comparison with Async/Await
===========================

Here, we compare ThingFlow to generic event-driven code using the new
``async`` / ``await`` language feature available starting with Python 3.5.

Scenario
--------
We wish to sample a sensor once every half second and:

1. Write the associated event to a CSV fle
2. Once every 5 samples, send the median of the last five samples to
   an MQTT queue for remote processing.

We have an asynchronous interface to the MQTT protocol (via hbmqtt),
which provides coroutines to establish a connection, publish a message, and
disconnect.

Event Version without Async/Await
---------------------------------
One could write an event-driven solution using the ``asyncio`` library
without the ``async`` and ``await`` statements. This will involve a large
number of callbacks and the resulting code will be very difficult to reason
about. See `this paper <http://dl.acm.org/citation.cfm?id=1244403>`__ for
an in-depth discussion of callback vs. coroutine event-driven programs.

Async/Await Implementation
--------------------------
Assuming we already have a transducer class for the queue output
and a (coroutine-based) adapter to the queue, we can create a coroutine for
sampling and sending the results downstream::

    async def sample_and_process(sensor, mqtt_writer, xducer):
        try:
            sample = sensor.sample()
        except StopIteration:
            final_event = xducer.complete()
            if final_event:
                await mqtt_writer.send((final_event.sensor_id, final_event.ts,
                                        final_event.val),)
            print("disconnecting")
            await mqtt_writer.disconnect()
            return False
        event = SensorEvent(sensor_id=sensor.sensor_id, ts=time.time(), val=sample)
        csv_writer(event)
        median_event = xducer.step(event)
        if median_event:
            await mqtt_writer.send((median_event.sensor_id, median_event.ts,
                                    median_event.val),)
        return True

The ``sample_and_process`` function must be a coroutine, as it calls coroutines
defined by the message queue adapter.

We now define global variables establish the main sampling loop::

    sensor = RandomSensor('sensor-2', stop_after_events=12)
    transducer = PeriodicMedianTransducer(5)
    event_loop = asyncio.get_event_loop()
    writer = MqttWriter(URL, sensor.sensor_id, event_loop)
    
    def loop():
        coro = sample_and_process(sensor, writer, transducer)
        task = event_loop.create_task(coro)
        def done_callback(f):
            exc = f.exception()
            if exc:
                raise exc
            elif f.result()==False:
                print("all done, no more callbacks to schedule")
                event_loop.stop()
            else:
                event_loop.call_later(0.5, loop)
        task.add_done_callback(done_callback)
        
    event_loop.call_soon(loop)
    event_loop.run_forever()  

The ``loop`` function schedules our coroutine and sets up a completion
callback (``done_callback``). This callback checks for errors and the
completion of the sensor. If neither of those happened, it reschedules
the loop to run in half a second.

ThingFlow Version
-----------------
In the ThingFlow version, state is maintained by each individual component, and
we can rely on the scheduler to deal with calling our task periodically.
Boundary events (errors and termination) are handled through a combination of
the scheduler and the individual AntEvent filters. Assuming we already have a
transducer class and an adapter to the queue, the entire code for this scenario
is::

    scheduler = Scheduler(asyncio.get_event_loop())
    sensor = SensorAsOutputThing(RandomSensor(SENSOR_ID, mean=10, stddev=5, stop_after_events=12))
    sensor.csv_writer('raw_data.csv'))
    q_writer = QueueWriter(URL, SENSOR_ID, scheduler)
    sensor.transduce(PeriodicMedianTransducer()).connect(q_writer)
    scheduler.schedule_periodic(sensor, 0.5)
    scheduler.run_forever()

After creating our sensor, we subscribe a CSV file writer. We then create a
second pipeline from the sensor, through the transducer, and to the queue.

Evaluation
----------
The async/await implementation largely follows a traditional procedural style. [1]_
Overall, the async/await has two disadvantages relative to ThingFlow:

1. The async nature of the coroutines is viral in the sense that any
   functions/methods calling an async (coroutine) method must also be
   async. This causes implementation decisions about whether to use
   asynchronous or synchronous APIs to have a non-local impact. In contrast,
   ThingFlow can support asynchronous APIs as well as components running
   in separate threads, without any application-level changes.
2. Each function in the async/await program's call stack must also have control
   flow to handle three possible situations: a normal event, an error, or the
   end of events from the upstream sensor. In ThingFlow, these are handled
   by the (reusable) components via the ``on_next``, ``on_error``, and
   ``on_completed`` methods. ThingFlow application code only needs to
   be concerned with the overall structure of the data flow.

ThingFlow achieves this simplicity by providing a level of indirection in the
programming model. The ThingFlow code actually generates the application by
connecting and configuring the requested components. The filter abstraction
used by the application programmer is at a much higher level than the procedural
abstractions used in an async/await application.


.. [1] An exception is the periodic scheduling of the sensor function, which requires
   the mutually recursive ``loop`` and ``done_callback`` callback functions.

Code
----
Full working code for both versions is available in this directory:
``asyncawait.py`` implements the scenario using coroutines and ``ant.py``
uses ThingFlow.
