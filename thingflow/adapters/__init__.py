# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
*Adapters* are components that connect ThingFlows to the external
world. *Readers* are event output things which source an event stream
into an ThingFlow process. *Writers* are input things that
translate an event stream to a form used outside of the ThingFlow
process. For example, `CsvReader` is a output thing that reads
events from a CSV-formatted spreadsheet file and `CsvWriter`
is an input thing that writes events to a CSV file.

Why don't we just call adapters OutputThings and InputThings? We
want to avoid confusion do to the fact that an OutputThing is used to connect
to external inputs while external outputs interface via InputThings.

"""
