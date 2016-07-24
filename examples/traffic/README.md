A collection of datasets of vehicle traffic, observed between two points for a set duration of time over a period of 
6 months (449 observation points in total). 

The original data was downloaded on 07.06.2016 from http://iot.ee.surrey.ac.uk:8080/datasets.html#traffic

The example sets up an AntEvents pipeline to read the data, compute sliding means, etc.

Here are some analyses carried out by the original European project:

TrafficCongestionStream: all the traffic events which have the average speed smaller than averageSpeedThreshold
and the number of cars bigger than vehicleCountThreshold.
Non-traffic congestion events are generated when the above mentioned pattern is no longer met.
A traffic jam event is generated when a traffic congestion event is not
followed by a non traffic congestion event in a time interval shorter than trafficCongestionLength.

(From http://www.ict-citypulse.eu/page/sites/default/files/d3.3_knowledge-based_event_detection_in_real_world_streams.pdf)




