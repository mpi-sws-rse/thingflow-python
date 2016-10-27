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
from bokeh.models import ColumnDataSource
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


class BokehPlotWorker(threading.Thread):
    def __init__(self, plotters):
        threading.Thread.__init__(self)
        self.plotters = plotters

    def update(self, whichq, whichsource):
        print("In update")
        try:
            data = whichq.get_nowait()
            if data:
                print('data = ', data)
                ts = data.ts
                val = data.val
                new_data = dict(timestamp=[ts], value=[val]) 
                whichsource.stream(new_data, 300)
        except queue.Empty:
            pass

    def make_fig(self, plot_source):
        plot_specs = plot_source['plot_specs']
        p = figure(plot_height=500, tools=TOOLS, y_axis_location='left', title=plot_specs.name)
        p.x_range.follow = "end"
        p.xaxis.axis_label = plot_specs.x_axis_label 
        p.yaxis.axis_label = plot_specs.y_axis_label 
        self.p.x_range.follow_interval = 100
        self.p.x_range.range_padding = 0 
        self.p.line(x=plot_specs.x_axis_label, y=plot_specs.y_axis_label, color="blue", source=plot_specs.source)
        self.p.circle(x=plot_specs.x_axis_label, y=plot_specs.y_axis_label, color="red", source=plot_specs.source)
        curdoc().add_periodic_callback(functools.partial(self.update, whichqueue=plot_source['queue'], whichsource=plot_specs.source), plot_specs.update_period) #period in ms

    def run(self):
        print("In thread.run")
        self.figs = map(self.make_fig, list(self.plotters))
        
        self.session = push_session(curdoc())
        self.session.show(column(self.figs)) 
        curdoc().title = 'AntEvent Streams' 
        self.session.loop_until_closed()



class BokehPlot(object):
    def __init__(self, name, y_axis_label="", x_axis_label="Time", update_period_in_ms=500):
        self.name = name
        self.x_axis_label = x_axis_label
        self.y_axis_label = y_axis_label
        self.update_period = update_period_in_ms
        self.source = ColumnDataSource(dict(x_axis_label=[], y_axis_label=[]))

class BokehPlotManager(object):
    def __init__(self):
        self.plots = { }
        self.open_for_registration = True
        self.started = False

    def register(self, plot):
        if self.open_for_registration: 
            self.plots[plot.name] = { 'queue' : queue.Queue(), 'plot_specs' : plot }
        else:
            raise Exception("Bokeh Adapter: Plot manager does not dynamically add registrations.")

    def start(self):
        self.open_for_registration = False
        self.bokeh_plot_worker = BokehPlotWorker(self.plots)
        self.bokeh_plot_worker.start()
        self.started = True


    def on_next(self, t): 
        whichplot, data = t
        assert self.started, "BokehPlotManager: Data sent without initialization"
        if whichplot in self.plots:
            self.plots[whichplot]['queue'].put(data)
        else:
            raise Exception("Plot %s not found among registered plots", whichplot)

    def on_completed(self):
        pass

    def on_error(self):
        pass

class BokehOutputWorker(threading.Thread):
    source = ColumnDataSource(dict(timestamp=[], value=[]))
    def __init__(self, sensor_id, datasource):
        threading.Thread.__init__(self)
        self.q = datasource
        self.title = sensor_id

        self.counter = 0

    def update(self):
        print("In update")
        try:
            data = self.q.get_nowait()
            if data:
                print('data = ', data)
                ts = data.ts
                val = data.val
                new_data = dict(timestamp=[ts], value=[val]) 
                self.source.stream(new_data, 300)
                self.counter = 0
        except queue.Empty:
            pass
            self.counter = self.counter + 1
            if self.counter == 10:
                exit(0)

    def run(self):
        print("In thread.run")
        self.p = figure(plot_height=500, tools=TOOLS, y_axis_location='left', title=self.title)
        self.p.x_range.follow = "end"
        self.p.xaxis.axis_label = "Timestamp"
        self.p.x_range.follow_interval = 100
        self.p.x_range.range_padding = 0 
        self.p.line(x="timestamp", y="value", color="blue", source=self.source)
        self.p.circle(x="timestamp", y="value", color="red", source=self.source)

        self.session = push_session(curdoc())
        curdoc().add_periodic_callback(self.update, 100) #period in ms

        self.session.show(column(self.p)) 
        curdoc().title = 'Sensor' 
        self.session.loop_until_closed()

    # def register(self, d, sourceq):
    #     source = ColumnDataSource(dict(d))
    #     self.p.line(x=d[0], y=d[1], color="orange", source=source)
    #     curdoc().add_periodic_callback(self.update, 100) #period in ms

class BokehStreamer(Filter):
    def __init__(self, initial_csv, io_loop=None):
        self.q = queue.Queue() 
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


