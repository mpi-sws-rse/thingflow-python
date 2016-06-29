"""Emuation for micropython's utime module
"""
from time import time, sleep

def ticks_ms():
    return time()*1000

def ticks_diff(old, new):
    return new - old

