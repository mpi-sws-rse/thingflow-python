"""Control NeoPixel-style light strips from ThingFlow.

num_pixels and bytes_per_pixel will vary, depending on your light strip.
Set pinno to the gpio pin number where you connected the data line of
the NeoPixel.

If you have bytes_per_pixel=3, the events will be of the form:
  (pixelno, r, g, b)

If you have bytes_per_pixel=4, the events will be of the form:
  (pixelno, r, g, b, w)
"""

from machine import Pin
from neopixel import NeoPixel

class NeoPixelWriter:
    def __init__(self, num_pixels=10, bytes_per_pixel=4, pinno=15):
        pin = Pin(pinno, Pin.OUT)
        self.np = NeoPixel(pin, num_pixels, bpp=bytes_per_pixel)
        self.bytes_per_pixel = bytes_per_pixel
        self.tuple_len = bytes_per_pixel+1

    def on_next(self, x):
        """The event should be a tuple/list where the first element
        is the pixel number and the rest are the settings for that pixel
        OR it can be a standard (sensor_id, ts, event) tuple, where the control
        message is in the third element.
        """
        if len(x)==3 and (isinstance(x[2], tuple) or isinstance(x[2], list)) and \
           len(x[2])==self.tuple_len:
            x = x[2] # the control message is embedded in a standard triple
        elif len(x)!=self.tuple_len:
            raise Exception("expecting a tuple of length %d" % self.tuple_len)
        pixel = x[0]
        self.np[pixel] = x[1:]
        self.np.write()

    def on_error(self, e):
        pass

    def on_completed(self):
        pass
