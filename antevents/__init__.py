"""
This is the main package for antevents. Directly within this package you fill
find the following modules:

 * `base` - the core abstractions and classes of the system.
 * `sensor` - defines data types and functions specifically for sensor events.

The rest of the functionality is in sub-packages:

 * `adapters` - components to read/write events outside the system
 * `internal` - some internal definitions
 * `linq` - filters that allow linq-style query pipelines over event streams
"""

__version__ = "1.0"
