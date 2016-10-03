"""Adapters for connecting time-series data to Bokeh visualizations
"""

"""Define an event type for time-series data from sensors.
from collections import namedtuple

# Define a sensor event as a tuple of sensor id, timestamp, and value.
# A 'sensor' is just a generator of sensor events.
SensorEvent = namedtuple('SensorEvent', ['sensor_id', 'ts', 'val'])

"""
import datetime
import logging

import threading, queue

from bokeh.charts import TimeSeries, show, output_file, output_server
from bokeh.plotting import figure, curdoc
from bokeh.layouts import column # to show two or more plots arranged in a column
import numpy as np
from bokeh.models import ColumnDataSource, Slider
from bokeh.client import push_session
from bokeh.driving import linear

from antevents.base import Filter, filtermethod

logger = logging.getLogger(__name__)

TOOLS="pan,wheel_zoom,box_zoom,reset,save"
tooltips=[
        ("Open", "@Open"),
        ("Close", "@Close"),
        ("High", "@High"),
        ("Low", "@Low"),
        ("Volume", "@Volume")
    ]


def bokeh_timeseries_mapper(events):
    # a row is 'timestamp', 'datetime', 'sensor_id', 'value'
    ts = [ ]
    dttm = [ ]
    value = [ ]
    for r in events:
        t = float(r.ts)
        print(t)
        # dt = datetime.datetime.utcfromtimestamp(t)
        ts.append(t)
        # dttm.append(r['datetime'])
        value.append(r.val)
    return { 'timestamp' : ts, 'value' : value } 
 
def bokeh_default_mapper(csv):
    return csv

def bokeh_output(csv, mapper=bokeh_timeseries_mapper):
    data = mapper(csv)
    print(data)
    p = figure(width=800, height=250)
    p.circle(data['timestamp'],  data['value'])
    p.line(data['timestamp'], data['value'])
    show(p)
    # tsline = TimeSeries(data, x = 'timestamp', y=[ 'value' ], legend=True,\
    #                     title="Sensor", tools=TOOLS, ylabel='Sensor readings', xlabel='Time') 
    # show(tsline)

source = ColumnDataSource(dict(timestamp=[], value=[]))

class BokehOutputWorker(threading.Thread):
    def __init__(self, sensor_id, datasource):
        threading.Thread.__init__(self)
        self.q = datasource
        self.counter = 0
        self.title = sensor_id

    def update(self):
        print("In update")
        try:
            data = self.q.get_nowait()
            if data:
                print('data = ', data)
                ts = data.ts
                val = data.val
                new_data = dict(timestamp=[ts], value=[val]) 
                source.stream(new_data, 300)
                self.counter = 0
        except queue.Empty:
            pass
            self.counter = self.counter + 1
            if self.counter == 10:
                exit(0)

    def run(self):
        print("In thread.run")
        self.p = figure(plot_height=500, tools=TOOLS, y_axis_location='left', title=self.title)
        # self.mean = Slider(title="mean", value=0, start=-0.01, end=0.01, step=0.001)
        self.p.x_range.follow = "end"
        self.p.xaxis.axis_label = "Timestamp"
        self.p.x_range.follow_interval = 100
        self.p.x_range.range_padding = 0 
        self.p.line(x="timestamp", y="value", color="blue", source=source)
        self.p.circle(x="timestamp", y="value", color="red", source=source)

        session = push_session(curdoc())
        curdoc().add_periodic_callback(self.update, 100) #period in ms

        session.show(column(self.p)) 
        curdoc().title = 'Sensor' 
        session.loop_until_closed()
 

class BokehStreamer(Filter):
    def __init__(self, initial_csv, mapper=bokeh_timeseries_mapper, io_loop=None):
        self.q = queue.Queue() 
        self.mapper = mapper
        self.bokeh_worker = BokehOutputWorker("Sensor", self.q)
        self.bokeh_worker.start()

 

    def on_next(self, x):
        print("next:", x)
        self.q.put(x)

    def on_completed(self):
        self.q.join()
        self.bokeh_worker.stop()
        self._dispatch_completed()

    def on_error(self, e):
        self.q.join()
        self._dispatch_error(e)

def bokeh_output_streaming(csv):
    """Write an event stream to a Bokeh visualizer
    """    
    b = BokehStreamer(csv)

