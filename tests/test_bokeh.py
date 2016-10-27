import asyncio
from utils import ValueListSensor, ValidationSubscriber
from antevents.base import Scheduler, SensorPub, SensorEvent

from antevents.linq.map import map
from antevents.adapters.bokeh import bokeh_output, bokeh_output_streaming, BokehStreamer, BokehPlot, BokehPlotManager
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

value_stream = [10, 13, 20, 20, 19, 19, 20, 21, 28, 28, 23, 21, 21, 18, 19, 16, 21,
                10, 13, 20, 20, 19, 19, 20, 21, 28, 28, 23, 21, 21, 18, 19, 16, 21]
value_stream2 = [2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6,
                 6, 2, 3, 2, 2, 9, 9, 2, 1, 8, 8, 3, 2, 1, 8, 9, 6, 2, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 6]

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

def test_bokeh_manager():
    loop = asyncio.get_event_loop()
    s1 = ValueListSensor(1, value_stream)
    p1 = SensorPub(s1)
    s2 = ValueListSensor(1, value_stream2)
    p2 = SensorPub(s2)

    bm = BokehPlotManager()
    bplot1 = BokehPlot('Sensor1', y_axis_label='value')  
    bplot2 = BokehPlot('Sensor2', y_axis_label='value')  
    bm.register(bplot1)
    bm.register(bplot2)
    p1.map(lambda v: ('Sensor1', v)  ).subscribe(bm)
    p2.map(lambda v: ('Sensor2', v)  ).subscribe(bm)
    bm.start()
 
    scheduler = Scheduler(loop)
    scheduler.schedule_periodic(p1, 1.0) # sample every second
    scheduler.schedule_periodic(p2, 0.5) # sample twice every second
    scheduler.run_forever()
    # self.assertTrue(vo.completed,
    #     "Schedule exited before validation observer completed")
    print("That's all folks")
    
if __name__ == "__main__":
    # test_bokeh_output()
    test_bokeh_manager()
