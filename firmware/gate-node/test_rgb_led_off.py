# Turns off the onboard addressable RGB LED (WS2812/NeoPixel). Its
# flickering/random-color behavior with no code running is expected for
# this type of LED - the data pin is left floating with nothing running,
# so it picks up electrical noise (nearby cable movement, USB replug) as
# random bit patterns. Once something actively drives the pin and writes
# an explicit color, it goes stable - here, off.
#
# RGB_PIN is a guess: GPIO48 is the most common pin for this LED on
# ESP32-S3 DevKitC-1 style boards. If this doesn't turn it off, check the
# board's silkscreen near the LED for a labeled pin, or try 38 next.

from machine import Pin
from neopixel import NeoPixel

RGB_PIN = 48

np = NeoPixel(Pin(RGB_PIN, Pin.OUT), 1)
np[0] = (0, 0, 0)
np.write()

print("RGB LED on GPIO%d set to off." % RGB_PIN)
