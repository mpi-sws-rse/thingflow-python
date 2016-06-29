# Utility functions and classes.

import sys


if sys.implementation.name=='micropython':
    def wifi_connect(essid, password):
        # Connect to the wifi. Based on the example in the micropython
        # documentation.
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            get_logger().info('connecting to network...')
            wlan.connect(essid, password)
            while not wlan.isconnected():
                pass
        get_logger().info('network config:', wlan.ifconfig())
else:
    # stub version for testing
    def wifi_connect(essid, password):
        get_logger().info('wifi_connect(%s, %s) [stub version]' %
                          (essid, password))


import time

# A really simple rotating logger
class Logger(object):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    WARN = WARNING
    ERROR = 40
    
    def __init__(self, outputfile, max_len, level=INFO,
                 interactive=False):
        # Specify a logfile, the max length of the file before rotating,
        # the minimum level to log, and whether this is being run interactivly.
        # If it is interactive, we also print messages in addition to saving
        # them to the file.
        self.outputfile = outputfile
        self.backupfile = outputfile + '.1'
        self.max_len = max_len
        self.level = level
        self.interactive = interactive
        self.size_written = 0
        import os
        try:
            os.stat(self.outputfile)
            # If we get here there is an old log file in place.
            # We force a rotation.
            self._rotate()
        except:
            self.fileobj = open(outputfile, 'w')

    def _write(self, levelname, msg):
        lt = time.localtime()
        data = '%d-%02d-%02d %02d:%02d:%02d [%s] %s\n' % \
               (lt[0], lt[1], lt[2], lt[3], lt[4], lt[5], levelname, msg)
        if (len(data) + self.size_written)>self.max_len:
            self.fileobj.close()
            self._rotate()
        self.fileobj.write(data)
        self.fileobj.flush()
        self.size_written += len(data)
        if self.interactive:
            print(data, end="")

    def _rotate(self):
        import os
        try:
            os.stat(self.backupfile)
            # this only gets run if the file exists
            os.remove(self.backupfile)
        except:
            pass
        print("running rotate")
        os.rename(self.outputfile, self.backupfile)
        self.size_written = 0
        self.fileobj = open(self.outputfile, 'w')

    def debug(self, msg):
        if self.level <= Logger.DEBUG:
            self._write('DBG', msg)
    def info(self, msg):
        if self.level <= Logger.INFO:
            self._write('INF', msg)
    def warning(self, msg):
        if self.level <= Logger.WARNING:
            self._write('WRN', msg)

    warn = warning # alias the shorthand for the lazy typists!
    
    def error(self, msg):
        if self.level <= Logger.ERROR:
            self._write('ERR', msg)

    def set_level(self, level):
        self.level = level

    def close(self):
        self.fileobj.close()
        self.fileobj = None

_logger = None


def initialize_logging(filename, max_len=32000, level=Logger.INFO,
                       interactive=False):
    global _logger
    if _logger!=None:
        raise Exception("Logger was already initialized!")
    _logger = Logger(filename, max_len, level, interactive)


def get_logger():
    global _logger
    if _logger!=None:
        return _logger
    else:
        raise Exception("Logger was not yet initialized!")

def close_logging():
    global _logger
    if _logger:
        _logger.close()
        _logger = None
