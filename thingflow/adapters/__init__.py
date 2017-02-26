# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
*Adapters* are components that connect antevents to the external
world. *Readers* are event publishers which source an event stream
into an antevent process. *Writers* are event subscribers that
translate an event stream to a form used outside of the antevent
process. For example, `CsvReader` is a publisher that reads
events from a CSV-formatted spreadsheet file and `CsvWriter`
is a subscriber that writes events to a CSV file.

Why don't we just call adapters publishers and subscribers? The problem
is that it can get confusing if the adapter is connecting to an actual
publish/subscribe system (e.g. an MQTT broker). The MQTT *reader* is a
*publisher* in the antevents world, but it must *subscribe* to a topic in
the MQTT world. Likewise, the MQTT *writer* is a *subscriber* in the antevents
world and *publishes* to a topic in MQTT.

"""
