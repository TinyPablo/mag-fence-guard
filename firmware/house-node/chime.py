"""Two bell tones streamed in small chunks to keep the control loop responsive."""

import math
import struct
from machine import Pin, I2S
from time import ticks_ms, ticks_diff, ticks_add

RATE = 16000


class Chime:
    def __init__(self):
        self.sound = bytearray()
        for frequency, duration_ms in ((880, 250), (660, 350)):
            count = RATE * duration_ms // 1000
            for i in range(count):
                envelope = min(1.0, i / 80) * (1 - i / count) ** 2
                sample = int(5000 * envelope * math.sin(2 * math.pi * frequency * i / RATE))
                self.sound.extend(struct.pack("<h", sample))
            self.sound.extend(bytes(RATE * 80 // 1000 * 2))
        self.sound = memoryview(self.sound)
        self.position = len(self.sound)
        self.speaker = None
        self.repeating = False
        self.started = 0
        self.next_ring = None
        self.resume()

    def resume(self):
        if self.speaker is not None:
            return
        self.speaker = I2S(1, sck=Pin(7), ws=Pin(8), sd=Pin(9),
                           mode=I2S.TX, bits=16, format=I2S.MONO,
                           rate=RATE, ibuf=1024)

    def ring(self, repeat=False):
        self.resume()
        self.position = 0
        self.repeating = repeat
        self.started = ticks_ms()
        self.next_ring = None

    def stop(self):
        self.position = len(self.sound)
        self.repeating = False
        self.next_ring = None
        # Discard queued chime samples immediately on answer/open/timeout.
        if self.speaker is not None:
            self.speaker.deinit()
            self.speaker = None

    def poll(self):
        now = ticks_ms()
        if self.repeating and ticks_diff(now, self.started) >= 30000:
            self.stop()
            return
        if self.repeating and self.position >= len(self.sound):
            if self.next_ring is None:
                self.next_ring = ticks_add(now, 900)
            elif ticks_diff(now, self.next_ring) >= 0:
                self.position = 0
                self.next_ring = None
        if self.speaker is not None and self.position < len(self.sound):
            end = min(self.position + 256, len(self.sound))
            written = self.speaker.write(self.sound[self.position:end])
            if written:
                self.position += written

    def release(self):
        self.stop()
        if self.speaker is not None:
            self.speaker.deinit()
            self.speaker = None

    def close(self):
        self.release()
