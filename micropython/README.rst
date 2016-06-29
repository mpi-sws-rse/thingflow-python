===========================
Ant Events Micropython Port
===========================

This is a port of Ant Events to Micropython_, a bare-metal implementation of
Python 3 for small processors. This port has been tested on the ESP8266_.

Micropython has only a subset of the libraries that come with the standard
CPython implementation. For example, an event library, threading, and even
logging are missing. This port currently only provides a subset of the
Ant Events functionality. Some of the APIs are a little different, too. These
will be made more consistent in time. The assumption is that processors like
the ESP8266 are used primarily to sample sensor data and pass it on to
a larger system (e.g. a Raspberry Pi or a server).

The entire implementation is in antevents.py.

_Micropython: http://www.micropython.org
_ESP8266: https://en.wikipedia.org/wiki/ESP8266


