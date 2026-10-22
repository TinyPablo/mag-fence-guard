"""Two bell tones streamed in small chunks to keep the control loop responsive."""

import math
import struct
from machine import Pin, I2S

RATE = 16000


class Chime:
    def __init__(self):
        self.sound = bytearray()
        for frequency in (1047, 1319):
            for i in range(RATE * 220 // 1000):
                envelope = min(1.0, i / 80) * (1 - i / 3520) ** 2
                sample = int(5000 * envelope * math.sin(2 * math.pi * frequency * i / RATE))
                self.sound.extend(struct.pack("<h", sample))
            self.sound.extend(bytes(RATE * 80 // 1000 * 2))
        self.sound = memoryview(self.sound)
        self.position = len(self.sound)
        self.speaker = None
        self.resume()

    def resume(self):
        if self.speaker is not None:
            return
        self.speaker = I2S(1, sck=Pin(7), ws=Pin(8), sd=Pin(9),
                           mode=I2S.TX, bits=16, format=I2S.MONO,
                           rate=RATE, ibuf=1024)

    def ring(self):
        self.resume()
        self.position = 0

    def stop(self):
        self.position = len(self.sound)

    def poll(self):
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
