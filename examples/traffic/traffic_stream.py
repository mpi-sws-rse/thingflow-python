import asyncio
import datetime
from collections import namedtuple

from antevents.base import Scheduler
import antevents.linq
from antevents.linq.transducer import Transducer
from antevents.adapters.csv import CsvReader, EventSpreadsheetMapping

TrafficEvent = namedtuple('TrafficEvent', ['ts', 'status', 'avgMeasuredTime', 'avgSpeed', 'extID', 'medianMeasuredTime', 'vehicleCount', 'id', 'report_id'])

class TrafficEventMapping(EventSpreadsheetMapping):
    def get_header_row(self):
        return ['status', 'avgMeasuredTime', 'avgSpeed', 'extID', 'medianMeasuredTime', 'TIMESTAMP', 'vehicleCount', '_id', 'REPORT_ID']

    def event_to_row(self, event):
        return [event.status,
                event.avgMeasuredTime, 
                event.avgSpeed, 
                event.extID, 
                event.medianMeasuredTime, 
                event.ts, 
                event.vehicleCount, 
                event.id, 
                event.report_id]

    def row_to_event(self, row):
        status = row[0]
        avgMeasuredTime = int(row[1])
        avgSpeed = int(row[2]) 
        extID = int(row[3])
        medianMeasuredTime = int(row[4]) 
        ts = datetime.datetime.strptime(row[5], "%Y-%m-%dT%H:%M:%S")
        vehicleCount = int(row[6])
        id = int(row[7])
        report_id = int(row[8])
        return TrafficEvent(ts=ts, status=status,  
                            avgMeasuredTime=avgMeasuredTime, 
                            avgSpeed=avgSpeed, 
                            extID=extID,  
                            medianMeasuredTime=medianMeasuredTime,  
                            vehicleCount=vehicleCount,  
                            id=id,  
                            report_id = report_id) 
    
traffic_event_mapper = TrafficEventMapping()

class TooManyErrors(Exception):
    pass

# A sanitizer "fixes" an event stream by 
class Sanitizer(Transducer):
    def __init__(self, drop_bad=True, threshold=100):
        self.drop_bad = drop_bad
        self.threshold = threshold
        self.errors  = 0
        self.old_event = None

    def step(self, event):
        if event.status == 'OK':
            self.errors = 0
            self.old_event = event
            return event
        else:
            self.errors  += 1 
            if self.errors > self.threshold:
                raise TooManyErrors
            if self.drop_bad or self.old_event is None:
                return None
            else:
                return self.old_event

    def __str__(self):
        return 'Sanitizer' 

class TrafficJamChecker(Transducer):
    def __init__(self, thresholdSpeed, thresholdVehicleCount, threshold=100):
        self.threshold = threshold
        self.thresholdSpeed = thresholdSpeed
        self.thresholdVehicleCount = thresholdVehicleCount
        self.ladder = 0
        self.event_stream = []

    def step(self, event):
        def to_string(ev):
            return "%s: %d cars@%d" % (ev.ts.strftime("%d-%m-%YY %H:%M:%S"), ev.vehicleCount, ev.avgSpeed)
        if event.avgSpeed < self.thresholdSpeed and event.vehicleCount > self.thresholdVehicleCount:
            self.ladder += 1
            self.event_stream.append(event)
            return None
        else:
            l = self.ladder
            es = self.event_stream
            self.ladder = 0
            self.event_stream = [ ] 
            if l > 0:
                return ("Traffic Jam %d rounds %s" % (l, [to_string(e) for e in es]))
            else:
                return None


    def __str__(self):
        return 'TrafficJamChecker' 

def main():
    thresholdSpeed = 50
    thresholdVehicleCount = 15
    trafficCongestionLength = 3

    csvstream = CsvReader('trafficData158324.csv', mapper=traffic_event_mapper)
    traffic_congestion = csvstream.transduce(Sanitizer(drop_bad=False, threshold=50)).transduce(TrafficJamChecker(thresholdSpeed, thresholdVehicleCount,threshold=3))

    traffic_congestion.subscribe(print)
    traffic_congestion.reduce((lambda acc, x: acc+1) , seed=0).subscribe(print)

    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_recurring(csvstream)


    try:
        scheduler.run_forever()
    except KeyboardInterrupt:
        scheduler.stop()

if __name__ == "__main__":
    main()
