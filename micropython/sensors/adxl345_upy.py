# ADXL345 Python library for Raspberry Pi 
#
# author:  Jonathan Williamson
# license: BSD, see LICENSE.txt included in this package
# 
# This is a Raspberry Pi Python implementation to help you get started with
# the Adafruit Triple Axis ADXL345 breakout board:
# http://shop.pimoroni.com/products/adafruit-triple-axis-accelerometer
#
# Minor edit to print statement for Python 3 and AntEvents API changes (need sensor_id)
# Edits for MicroPython (no smbus module)

from machine import I2C, Pin
from time import sleep

# select the correct i2c bus for this revision of Raspberry Pi
#revision = ([l[12:-1] for l in open('/proc/cpuinfo','r').readlines() if l[:8]=="Revision"]+['0000'])[0]
#bus = smbus.SMBus(1 if int(revision, 16) >= 4 else 0)
bus = I2C(scl = Pin(5), sda = Pin(4), freq = 100000)

# ADXL345 constants
EARTH_GRAVITY_MS2   = 9.80665
SCALE_MULTIPLIER    = 0.004

DATA_FORMAT         = 0x31
BW_RATE             = 0x2C
POWER_CTL           = 0x2D

BW_RATE_1600HZ      = [0x0F]
BW_RATE_800HZ       = [0x0E]
BW_RATE_400HZ       = [0x0D]
BW_RATE_200HZ       = [0x0C]
BW_RATE_100HZ       = [0x0B]
BW_RATE_50HZ        = [0x0A]
BW_RATE_25HZ        = [0x09]

RANGE_2G            = 0x00
RANGE_4G            = 0x01
RANGE_8G            = 0x02
RANGE_16G           = 0x03

MEASURE             = [0x08]
AXES_DATA           = 0x32

class ADXL345_upy:

    address = None

    def __init__(self, sensor_id, address = 0x53):     
        self.sensor_id = sensor_id   
        self.address = address
        self.setBandwidthRate(BW_RATE_100HZ)
        self.setRange(RANGE_2G)
        self.enableMeasurement()

    def enableMeasurement(self):
        bus.writeto_mem(self.address, POWER_CTL, bytearray(MEASURE))

    def setBandwidthRate(self, rate_flag):
        bus.writeto_mem(self.address, BW_RATE, bytearray(rate_flag))

    # set the measurement range for 10-bit readings
    def setRange(self, range_flag):
        value = bus.readfrom_mem(self.address, DATA_FORMAT,1)

        val2 = value[0]
        val2 &= ~0x0F;
        val2 |= range_flag;  
        val2 |= 0x08;
        buf = [val2]
        
        bus.writeto_mem(self.address, DATA_FORMAT, bytearray(buf))
    
    # returns the current reading from the sensor for each axis
    #
    # parameter gforce:
    #    False (default): result is returned in m/s^2
    #    True           : result is returned in gs
    def sample(self, gforce = False):
        #bytes = bus.read_i2c_block_data(self.address, AXES_DATA, 6)
        bytes = bus.readfrom_mem(self.address, AXES_DATA, 6)
        
        x = bytes[0] | (bytes[1] << 8)
        if(x & (1 << 16 - 1)):
            x = x - (1<<16)

        y = bytes[2] | (bytes[3] << 8)
        if(y & (1 << 16 - 1)):
            y = y - (1<<16)

        z = bytes[4] | (bytes[5] << 8)
        if(z & (1 << 16 - 1)):
            z = z - (1<<16)

        x = x * SCALE_MULTIPLIER 
        y = y * SCALE_MULTIPLIER
        z = z * SCALE_MULTIPLIER

        if gforce == False:
            x = x * EARTH_GRAVITY_MS2
            y = y * EARTH_GRAVITY_MS2
            z = z * EARTH_GRAVITY_MS2

        x = round(x, 4)
        y = round(y, 4)
        z = round(z, 4)

        return {"x": x, "y": y, "z": z}

if __name__ == "__main__":
    # if run directly we'll just create an instance of the class and output 
    # the current readings
    adxl345 = ADXL345()
    
    axes = adxl345.sample(True)
    print("ADXL345 on address 0x%x:" % (adxl345.address))
    print("   x = %.3fG" % ( axes['x'] ))
    print("   y = %.3fG" % ( axes['y'] ))
    print("   z = %.3fG" % ( axes['z'] ))
