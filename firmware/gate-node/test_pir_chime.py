# Same as test_pir_motion.py, but plays a short, quiet two-tone chime
# through the speaker on each idle -> motion transition, instead of/along
# with the printed log - so you can test PIR range/timing by ear while
# adjusting the sensor's distance and time-delay potentiometers.
#
# The chime is a soft descending "ding-dong" (two sine tones with a fade
# in/out envelope, no hard edges/clicks), kept quiet on purpose - only
# plays once per idle->motion edge, not continuously while motion holds.
#
# Wiring: PIR OUT=GPIO13, VCC=5V, GND=GND.
#         MAX98357A Vin=5V, GND=GND, LRC=GPIO8, BCLK=GPIO7, DIN=GPIO9,
#         GAIN=floating (default ~9dB), SD=3.3V (enable)

import math
import struct
from machine import Pin, I2S
from time import sleep_ms, ticks_ms

PIR_PIN = 13

SPK_SCK_PIN = 7
SPK_WS_PIN = 8
SPK_SD_PIN = 9

RATE = 16000
AMPLITUDE = 4000  # quiet on purpose (full scale is 32767)


def tone(freq, duration_ms):
    n = RATE * duration_ms // 1000
    fade = max(1, n // 8)  # linear fade in/out to avoid clicks
    samples = bytearray(n * 2)
    for i in range(n):
        envelope = 1.0
        if i < fade:
            envelope = i / fade
        elif i > n - fade:
            envelope = (n - i) / fade
        value = int(AMPLITUDE * envelope * math.sin(2 * math.pi * freq * i / RATE))
        struct.pack_into("<h", samples, i * 2, value)
    return samples


CHIME = tone(880, 150) + tone(660, 200)

pir = Pin(PIR_PIN, Pin.IN)
speaker = I2S(1, sck=Pin(SPK_SCK_PIN), ws=Pin(SPK_WS_PIN), sd=Pin(SPK_SD_PIN),
              mode=I2S.TX, bits=16, format=I2S.MONO, rate=RATE, ibuf=20000)

print("Watching PIR on GPIO%d. Move in front of the sensor." % PIR_PIN)

last_state = pir.value()
print("Initial state:", "MOTION" if last_state else "idle", "at", ticks_ms())

try:
    while True:
        state = pir.value()
        if state != last_state:
            print("MOTION" if state else "idle", "at", ticks_ms())
            if state:
                speaker.write(CHIME)
            last_state = state
        sleep_ms(20)
except KeyboardInterrupt:
    pass
finally:
    speaker.deinit()
    print("Stopped.")
