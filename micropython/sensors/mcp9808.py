# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Ported from Adafruit code for Raspberry Pi
# https://github.com/adafruit/Adafruit_Python_MCP9808/


# Default I2C address for device.
MCP9808_I2CADDR_DEFAULT        = 0x18

# Register addresses.
MCP9808_REG_CONFIG             = 0x01
MCP9808_REG_UPPER_TEMP         = 0x02
MCP9808_REG_LOWER_TEMP         = 0x03
MCP9808_REG_CRIT_TEMP          = 0x04
MCP9808_REG_AMBIENT_TEMP       = 0x05
MCP9808_REG_MANUF_ID           = 0x06
MCP9808_REG_DEVICE_ID          = 0x07

# Configuration register values.
MCP9808_REG_CONFIG_SHUTDOWN    = 0x0100
MCP9808_REG_CONFIG_CRITLOCKED  = 0x0080
MCP9808_REG_CONFIG_WINLOCKED   = 0x0040
MCP9808_REG_CONFIG_INTCLR      = 0x0020
MCP9808_REG_CONFIG_ALERTSTAT   = 0x0010
MCP9808_REG_CONFIG_ALERTCTRL   = 0x0008
MCP9808_REG_CONFIG_ALERTSEL    = 0x0002
MCP9808_REG_CONFIG_ALERTPOL    = 0x0002
MCP9808_REG_CONFIG_ALERTMODE   = 0x0001

from machine import I2C, Pin

def _bytes_to_int_be(data):
    return data[1] + (data[0]<<8)

class Mcp9808(object):
    """Class to represent an Adafruit MCP9808 precision temperature measurement
    board.
    """
    def __init__(self, sensor_id='mcp9808',
                 address=MCP9808_I2CADDR_DEFAULT, scl_pinno=5, sda_pinno=4,
                 i2c=None):
        """Initialize MCP9808 device on the specified I2C address and bus number.
        Address defaults to 0x18 and bus number defaults to the appropriate bus
        for the hardware.
        """
        self.sensor_id = sensor_id
        if i2c is None:
            self.i2c = I2C(scl=Pin(scl_pinno, Pin.IN),sda=Pin(sda_pinno, Pin.IN))
        else:
            self.i2c = i2c
        self.address=address
        assert self.begin(), "Invalid values read from I2C bus for MCP9808"

    def _read_uint16(self, register):
        return _bytes_to_int_be(self.i2c.readfrom_mem(self.address,register,
                                                              2))
    def begin(self):
        """Start taking temperature measurements. Returns True if the device is 
        intialized, False otherwise.
        """
        # Check manufacturer and device ID match expected values.
        mid = self._read_uint16(MCP9808_REG_MANUF_ID)
        did = self._read_uint16(MCP9808_REG_DEVICE_ID)
        print('Read manufacturer ID: {0:04X}'.format(mid))
        print('Read device ID: {0:04X}'.format(did))
        return mid == 0x0054 and did == 0x0400

    def sample(self):
        """Read sensor and return its value in degrees celsius."""
        # Read temperature register value.
        t = self._read_uint16(MCP9808_REG_AMBIENT_TEMP)
        # Scale and convert to signed value.
        temp = (t & 0x0FFF) / 16.0
        if t & 0x1000:
            temp -= 256.0
        return temp
