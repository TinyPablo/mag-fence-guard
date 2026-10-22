"""Nonblocking PIR warm-up and one exit trigger per post-lock LOW/HIGH cycle."""

from time import ticks_ms, ticks_diff


class PirExit:
    def __init__(self, warmup_ms=60000):
        if not isinstance(warmup_ms, int) or not 0 <= warmup_ms <= 600000:
            raise ValueError('PIR_WARMUP_MS must be 0..600000')
        self.warmup_ms = warmup_ms
        self.started = ticks_ms()
        self.ready = False
        self.armed = False
        self.low_since = None
        print('PIR exit: warmup_ms=%d; other gate functions remain available' % warmup_ms)

    def update(self, high, unlocked):
        now = ticks_ms()
        if ticks_diff(now, self.started) < self.warmup_ms:
            return False
        if not self.ready:
            self.ready = True
            print('PIR exit ready; waiting for LOW before arming')
        if unlocked:
            self.armed = False
            self.low_since = None
            return False
        if not high:
            if self.low_since is None:
                self.low_since = now
            if ticks_diff(now, self.low_since) >= 200:
                self.armed = True
            return False
        self.low_since = None
        if self.armed:
            self.armed = False
            return True
        return False


MODULE_VERSION = "0.6.0"
