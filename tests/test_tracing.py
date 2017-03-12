import asyncio
from thingflow.base import *
from utils import ValueListSensor
from thingflow.filters.map import map
from thingflow.filters.output import output
from thingflow.filters.combinators import passthrough

values = [1,2,3,4,5]
s = ValueListSensor(1, values)
p = SensorAsOutputThing(s)
p.passthrough(output).map(lambda x : x.val+1).output()
p.trace_downstream()

scheduler = Scheduler(asyncio.get_event_loop())
scheduler.schedule_periodic(p, 0.5) # sample twice every second
scheduler.run_forever()
