# Diagnostic version of test_rfid_interrupt.py - same arm_irq()/IRQ flow,
# but logs the timing around every arm/retry/detection so flaky behavior
# ("sometimes instant, sometimes needs a long hold, sometimes nothing")
# can actually be measured instead of guessed at. Also prints the raw
# ComIrqReg value read at IRQ time, so a real RxIRq hit can be told apart
# from a spurious pin wiggle.
#
# Reads on GPIO21 low: reads ComIrqReg (0x04) directly - bit5 (0x20) is
# RxIRq. If that bit is 0 when the pin fires, something other than a real
# tag response triggered the interrupt (noise, bad pull-up, etc).
#
# Wiring: same as test_rfid_interrupt.py (SCK=12, MOSI=11, MISO=10, CS=17,
# RST=16, IRQ=21).

from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms
from lib.mfrc522 import MFRC522

IRQ_PIN = 21
RETRY_MS = 200

reader = MFRC522(sck=12, mosi=11, miso=10, rst=16, cs=17)
irq_pin = Pin(IRQ_PIN, Pin.IN, Pin.PULL_UP)

tag_ready = False


def on_irq(pin):
    global tag_ready
    tag_ready = True


irq_pin.irq(trigger=Pin.IRQ_FALLING, handler=on_irq)

print("Watching for a tag via IRQ on GPIO%d (diagnostic build)..." % IRQ_PIN)

reader.arm_irq()
armed_at = ticks_ms()
retry_count = 0

while True:
    now = ticks_ms()

    if tag_ready:
        tag_ready = False
        latency = ticks_diff(now, armed_at)
        irq_reg = reader._rreg(0x04)
        rx_irq_set = bool(irq_reg & 0x20)

        reader.disarm_irq()
        status, raw_uid = reader.anticoll()

        if status == reader.OK:
            uid = "-".join("{:02X}".format(b) for b in raw_uid[:4])
            print("HIT  uid=%s  latency_ms=%d  retries=%d  ComIrqReg=0x%02X  RxIRq=%s"
                  % (uid, latency, retry_count, irq_reg, rx_irq_set))
        else:
            print("MISS (anticoll failed after IRQ)  latency_ms=%d  retries=%d  ComIrqReg=0x%02X  RxIRq=%s"
                  % (latency, retry_count, irq_reg, rx_irq_set))

        reader.arm_irq()
        armed_at = ticks_ms()
        retry_count = 0

    elif ticks_diff(now, armed_at) > RETRY_MS:
        reader.arm_irq()
        armed_at = now
        retry_count += 1
        if retry_count % 10 == 0:
            print("... still waiting, %d retries so far" % retry_count)

    sleep_ms(5)
