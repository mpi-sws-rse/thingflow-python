26
"""Demo of lux sensor and led from raspberry pi

"""
import sys
import asyncio
import os.path

from antevents.base import Scheduler
from antevents.adapters.rpi.lux_sensor import LuxSensor
from antevents.adapters.rpi.gpio import GpioPinOut
import antevents.adapters.csv
import antevents.linq.select

    
            

def setup(threshold=25):
    lux = LuxSensor()
    lux.subscribe(print)
    lux.csv_writer(os.path.expanduser('~/lux.csv'))
    led = GpioPinOut()
    actions = lux.map(lambda event: event.val > threshold)
    actions.subscribe(led)
    actions.subscribe(lambda v: print('ON' if v else 'OFF'))
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
