# Copyright 2016, 2017 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""
This is the main package for antevents. Directly within this package you fill
find the following module:

 * `base` - the core abstractions and classes of the system.

The rest of the functionality is in sub-packages:

 * `adapters` - components to read/write events outside the system
 * `internal` - some internal definitions
 * `filters` - filters that allow linq-style query pipelines over event streams
 * `sensors` - interfaces to sensors go here
"""

__version__ = "2.3.0"
