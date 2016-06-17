import asyncio

from antevents.base import *
from utils import make_test_sensor
import antevents.linq.where
import antevents.linq.output
import antevents.linq 
from antevents.linq.never import Never

loop = asyncio.get_event_loop()
        
s = make_test_sensor(1, stop_after_events=5)
 
t = s.skip(2).some(lambda x: x[2]>100)

s.subscribe(print)
t.subscribe(print)

scheduler = Scheduler(loop)
scheduler.schedule_periodic(s, 2) # sample once every 2 seconds


u = s.take_last(3).scan(lambda a, x: a+x[2], 0)
u.subscribe(print)
v = s.take_last(3).reduce(lambda a, x: a+x[2], 0)
v.subscribe(print)

def pp_buf(x):
    print("Buffered output: ", x)
    print("\n")

w = s.buffer_with_time(5, scheduler)
w.subscribe(pp_buf)
# w = Never()
# w.subscribe(print)
# scheduler.schedule_periodic(w, 1)

s.print_downstream()

loop.call_later(30, scheduler.stop)

scheduler.run_forever()
print("That's all folks")

