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

    def on_next(self, x):
        """The event should be a tuple/list where the first element
        is the pixel number and the rest are the settings for that pixel.
        """
        assert len(x)==(self.bytes_per_pixel+1),\
            "expecting a tuple of length %d" % (self.bytes_per_pixel+1)
        pixel = x[0]
        self.np[pixel] = x[1:]
        self.np.write()

    def on_error(self, e):
        pass

    def on_completed(self):
        pass
