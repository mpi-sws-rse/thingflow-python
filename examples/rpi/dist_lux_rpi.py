"""Demo of lux sensor and led from raspberry pi - distributed version.
This file contains the data capture part that runs on the Raspberry Pi.
"""
import sys
import asyncio
import argparse

from antevents.base import Scheduler, SensorPub
from antevents.sensors.rpi.lux_sensor import LuxSensor
from antevents.adapters.rpi.gpio import GpioPinOut
from antevents.adapters.mqtt import MQTTWriter
import antevents.linq.select
import antevents.linq.json


def setup(broker, threshold):
    lux = SensorPub(LuxSensor())
    lux.subscribe(print)
    led = GpioPinOut()
    actions = lux.map(lambda event: event.val > threshold)
    actions.subscribe(led)
    actions.subscribe(lambda v: print('ON' if v else 'OFF'))
    lux.to_json().subscribe(MQTTWriter(broker, topics=[('bogus/bogus', 0)]))
    lux.print_downstream()
    return (lux, led)
    

def main(argv=sys.argv[1:]):
    parser=argparse.ArgumentParser(description='Distributed lux example, data capture process')
    parser.add_argument('-i', '--interval', type=float, default=5.0,
                        help="Sample interval in seconds")
    parser.add_argument('-t', '--threshold', type=float, default=25.0,
                        help="Threshold lux level above which light should be turned on")
    parser.add_argument('broker', metavar="BROKER",
                        type=str,
                        help="hostname or ip address of mqtt broker")
    parsed_args = parser.parse_args(argv)
    (lux, led) = setup(parsed_args.broker, parsed_args.threshold)
    scheduler = Scheduler(asyncio.get_event_loop())
    stop = scheduler.schedule_periodic_on_separate_thread(lux,
                                                          parsed_args.interval)
    print("starting run...")
    try:
        scheduler.run_forever()
    except KeyboardInterrupt:
        led.on_completed()
        stop()
    return 0

if __name__ == '__main__':
    main()
