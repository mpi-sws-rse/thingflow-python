===========================
Comparison with Async/Await
===========================

Here, we compare AntEvents to generic event-driven code using the new
async/await language feature available starting with Python 3.5.

Scenario
--------
We wish to sample a sensor once every half second and:

1. Write the associated event to a CSV fle
2. Once every 5 samples, send the median of the last five samples to
   an MQTT queue for remote processing.

We have an asynchronous interface to the MQTT protocol, which provides
coroutines to establish a connection, publish a message, and disconnect.

Event Version without Async/Await
---------------------------------
One could write an event-driven solution using the ``asyncio`` library
without the ``async`` and ``await`` statements. This will involve a large
number of callbacks and the resulting code will be very difficult to reason
about.

Async/Await Implementation
--------------------------
Assuming we already have a transducer class for the queue output
and a (coroutine-based) adapter to the queue, we can create a class for sampling
and sending the results downstream::

    class ProcessSensor:
        def __init__(self, sensor, url, event_loop):
            self.sensor = sensor
            self.xduce = PeriodicMedianTransducer(5)
            self.q = MqttWriter(url, sensor.sensor_id, event_loop)
    
        async def sample_and_process(self):
            try:
                sample = self.sensor.sample()
            except StopIteration:
                print("disconnecting")
                await self.q.disconnect()
                return False
            event = SensorEvent(sensor_id=self.sensor.sensor_id, ts=time.time(), val=sample)
            csv_writer(event)
            median_event = self.xduce.step(event)
            if median_event:
                await self.q.send((median_event.sensor_id, median_event.ts, median_event.val),)
            return True

The ``sample_and_process`` method must be a coroutine, as it calls coroutines
defined by the message queue adapter.

We now must establish the main sampling loop::

    sensor = RandomSensor('sensor-2', stop_after_events=12)
    event_loop = asyncio.get_event_loop()
    process = ProcessSensor(sensor, URL, event_loop)
    def loop():
        coro = process.sample_and_process()
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

AntEvents Version
-----------------
In the AntEvents version, state is maintained by each individual component, and
we can rely on the scheduler to deal with calling our task periodically and to
handle boundry events. Assuming we already have a transducer class and an
adapter to the queue, the entire code for this scenario is::

    scheduler = Scheduler(asyncio.get_event_loop())
    sensor = SensorPub(RandomSensor(SENSOR_ID, mean=10, stddev=5, stop_after_events=12))
    sensor.csv_writer('raw_data.csv'))
    q_writer = QueueWriter(URL, SENSOR_ID, scheduler)
    sensor.transduce(PeriodicMedianTransducer()).subscribe(q_writer)
    scheduler.schedule_periodic(sensor, 0.5)
    scheduler.run_forever()

After creating our sensor, we subscribe a CSV file writer. We then create a
second pipeline from the sensor, through the transducer, and to the queue.

Evaluation
----------
In addition to being shorter, the AntEvents version makes the data flow
much clearer.


