"""Restore lost RC522 configuration without blocking the intercom loop."""

from time import ticks_ms, ticks_diff

# Compare stable configuration only, not transient IRQ/FIFO/command state.
EXPECTED = ((0x14, 0x03, 0x03), (0x2A, 0xFF, 0x8D),
            (0x2B, 0xFF, 0x3E), (0x2C, 0xFF, 0x00),
            (0x2D, 0xFF, 0x1E), (0x15, 0xFF, 0x40),
            (0x11, 0xFF, 0x3D))


class Recovery:
    def __init__(self, reader):
        self.reader = reader
        self.last_check = ticks_ms()
        self.last_attempt = None
        self.started = 0
        self.state = "healthy"
        self.attempts = 0
        self.restored = 0
        self.failures = 0

    def mismatch(self):
        for address, mask, expected in EXPECTED:
            value = self.reader._rreg(address)
            if value & mask != expected:
                return "reg=0x%02X value=0x%02X expected=0x%02X mask=0x%02X" % (
                    address, value, expected, mask)
        return None

    def fail(self, reason):
        self.failures += 1
        self.state = "failed"
        print("RFID recovery failed:", reason, "retry in 15 seconds")

    def poll(self):
        """True suspends tag exchanges; False permits normal RFID service."""
        now = ticks_ms()
        if self.state == "resetting":
            elapsed = ticks_diff(now, self.started)
            if elapsed < 50:
                return True
            try:
                if self.reader._rreg(0x01) & 0x10:
                    if elapsed >= 150:
                        self.fail("reset readiness timeout")
                    return True
                self.reader.init(reset=False)
                reason = self.mismatch()
                if reason:
                    self.fail(reason)
                    return True
                self.restored += 1
                self.state = "healthy"
                self.last_check = now
                print("RFID configuration restored; attempts=%d restored=%d failures=%d" %
                      (self.attempts, self.restored, self.failures))
                return False
            except OSError as error:
                self.fail(error)
                return True
        if self.state == "healthy":
            if ticks_diff(now, self.last_check) < 1000:
                return False
            self.last_check = now
            try:
                reason = self.mismatch()
            except OSError as error:
                reason = str(error)
            if reason is None:
                return False
            self.state = "failed"
            print("RFID configuration lost:", reason)
        if self.last_attempt is not None and ticks_diff(now, self.last_attempt) < 15000:
            return True
        self.last_attempt = now
        self.started = now
        self.attempts += 1
        try:
            self.reader._wreg(0x02, 0x80)
            self.reader._wreg(0x01, 0x0F)
            self.state = "resetting"
            print("RFID automatic reset; attempt:", self.attempts)
        except OSError as error:
            self.fail(error)
        return True


MODULE_VERSION = "0.5.0"
