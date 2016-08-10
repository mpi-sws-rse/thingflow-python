"""Demo of lux sensor and led from raspberry pi - distributed version.
This file contains the data capture part that runs on the Raspberry Pi.
"""
import sys
import asyncio

from antevents.base import Scheduler, SensorPub
from antevents.sensors.rpi.lux_sensor import LuxSensor
from antevents.adapters.rpi.gpio import GpioPinOut
from antevents.adapters.mqtt import MQTTWriter
import antevents.linq.select
import antevents.linq.json

BROKER_HOST='localhost'
            

def setup(threshold=25):
    lux = SensorPub(LuxSensor())
    lux.subscribe(print)
    led = GpioPinOut()
    actions = lux.map(lambda event: event.val > threshold)
    actions.subscribe(led)
    actions.subscribe(lambda v: print('ON' if v else 'OFF'))
    lux.to_json().subscribe(MQTTWriter(BROKER_HOST, topics=[('bogus/bogus', 0)]))
    lux.print_downstream()
    return (lux, led)
    

def main(argv=sys.argv[1:]):
    if len(argv)!=2:
        print("%s threshold interval" % sys.argv[0])
        return 1
    threshold = float(argv[0])
    interval = float(argv[1])
    print("%f seconds interval and an led threshold of %f lux" %
          (interval, threshold))
    (lux, led) = setup(threshold)
    scheduler = Scheduler(asyncio.get_event_loop())
    stop = scheduler.schedule_periodic_on_separate_thread(lux, interval)
    print("starting run...")
    try:
        scheduler.run_forever()
    except KeyboardInterrupt:
        led.on_completed()
        stop()
    return 0

if __name__ == '__main__':
    main()
