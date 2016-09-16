# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
import asyncio

from antevents.tcpstreamer import TcpStreamObserver
from antevents.base import make_test_publisher, Scheduler


loop = asyncio.get_event_loop()

s = make_test_publisher(1, stop_after_events=10)

t = TcpStreamObserver(loop, "localhost", 2991) 

s.subscribe(t)

scheduler = Scheduler(loop)
scheduler.schedule_periodic(s, 2) # sample once every 2 seconds


scheduler.run_forever()
scheduler.stop()
