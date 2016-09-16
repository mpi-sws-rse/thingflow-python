# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
"""Emulation of ESP8266 network layer
"""

STA_IF = 1

class WLAN:
    def __init__(self, interface_id):
        self.interface_id = interface_id
        self.is_active = False
        self.connected = False
        self.essid = None

    def active(self, make_active):
        if make_active:
            self.is_active = True
        else:
            self.is_active = False
            self.connected = False
            self.essid = None
            
    def isconnected(self):
        return self.connected

    def connect(self, essid, password):
        self.connected = True
        self.essid = essid

    def ifconfig(self):
        return self.essid
