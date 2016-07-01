"""This just simulates a remote esp8266 node for testing purposes.
It publishes events to the local broker.
"""
import sys
import asyncio
import time

from antevents.base import Scheduler, IterableAsPublisher
from antevents.adapters.mqtt import MQTTWriter
import antevents.linq.select
import antevents.linq.json

BROKER_HOST='127.0.0.1'
SENSOR1_ID='front-room'
SENSOR2_ID='back-room'
            
def make_event(sensor_id, val):
    return [sensor_id, time.time(), val]

def event_generator(sensor_id, values):
    for v in values:
        print("generating event for %s" % v)
        yield make_event(sensor_id, v)

def setup():
    lux1 = IterableAsPublisher(event_generator(SENSOR1_ID, [20, 20, 30, 40, 20]),
                               name=SENSOR1_ID)
    lux1.output()
    print("Initializing writer...")
    writer = MQTTWriter(BROKER_HOST, client_id=SENSOR1_ID, topics=[('remote-sensors', 0)])
    print("Writer connected")
    lux1.to_json().subscribe(writer)
    lux1.print_downstream()
    lux2 = IterableAsPublisher(event_generator(SENSOR2_ID, [10, 10, 20, 10, 10]),
                               name=SENSOR2_ID)
    lux2.to_json().subscribe(writer)
    lux2.output()
    lux2.print_downstream()
    return lux1, lux2
    

def main(argv=sys.argv[1:]):
    if len(argv)!=1:
        print("%s interval" % sys.argv[0])
        return 1
    interval = float(argv[0])
    print("%f seconds interval" % interval)
    lux1, lux2 = setup()
    scheduler = Scheduler(asyncio.get_event_loop())
    stop1 = scheduler.schedule_periodic(lux1, interval)
    stop2 = scheduler.schedule_periodic(lux2, interval)
    print("starting run...")
    try:
        scheduler.run_forever()
    except KeyboardInterrupt:
        stop1()
        stop2()
    return 0

if __name__ == '__main__':
    main()
