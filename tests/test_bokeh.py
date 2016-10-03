import asyncio
from utils import ValueListSensor, ValidationSubscriber
from antevents.base import Scheduler, SensorPub, SensorEvent

from antevents.adapters.bokeh import bokeh_output, bokeh_output_streaming, BokehStreamer
import datetime, time

def mk_csv():
    sid = 'temp'
    val = 0
    csv = [ ]
    for i in range(3):
        ts = time.mktime(datetime.datetime.now().timetuple())
        dt = ts
        val = val + 1
        csv.append([SensorEvent(ts=ts, sensor_id=sid, val=val)])
        time.sleep(1)
    return csv 

def debug():
    csv = mk_csv()
    bokeh_output(csv)
    bokeh_output_streaming(csv)

value_stream = [10, 13, 20, 20, 19, 19, 20, 21, 28, 28, 23, 21, 21, 18, 19, 16, 21]

def test_bokeh_output():
    loop = asyncio.get_event_loop()
    s = ValueListSensor(1, value_stream)
    p = SensorPub(s)
    b = BokehStreamer([ SensorEvent(ts=0,val=10,sensor_id="temp" ) ], io_loop=loop)
    p.subscribe(b)
 
    scheduler = Scheduler(loop)
    scheduler.schedule_periodic(p, 0.5) # sample twice every second
    scheduler.run_forever()
    self.assertTrue(vo.completed,
        "Schedule exited before validation observer completed")
    print("That's all folks")


if __name__ == "__main__":
    #debug()
    test_bokeh_output()
