"""Emuation for micropython's utime module
"""
import time

def ticks_ms():
    return time.time()*1000

def ticks_diff(old, new):
    return new - old

time = time.time
