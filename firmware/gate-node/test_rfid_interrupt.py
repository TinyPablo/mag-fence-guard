# Interrupt-driven RFID detection, retrying the approach dropped in
# docs/rfid.md - this time using MFRC522.arm_irq() (see lib/mfrc522.py),
# which arms a narrow RxIEn-only interrupt mask before sending REQA, so the
# physical IRQ pin only fires on a real tag response instead of also
# firing on the internal command timeout (the reason the earlier attempt
# failed).
#
# Flow: arm_irq() sends REQA and arms the pin -> wait for GPIO21 to go low
# (real tag) OR a host-side retry timeout (no tag yet, re-arm and resend
# REQA - this replaces the RC522's own timer interrupt, which is exactly
# what caused the false fires before) -> on a real hit, read the UID with
# anticoll() (ordinary SPI, no IRQ involved) and re-arm for the next tag.
#
# Wiring: same SPI pins as test_rfid.py (SCK=12, MOSI=11, MISO=10, CS=17,
# RST=16), plus IRQ=21. The RC522 IRQ pin is open-drain, active-low, so
# GPIO21 needs the internal pull-up (set below).

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

print("Watching for a tag via IRQ on GPIO%d..." % IRQ_PIN)

reader.arm_irq()
last_arm_ms = ticks_ms()

while True:
    if tag_ready:
        tag_ready = False
        reader.disarm_irq()
        status, raw_uid = reader.anticoll()
        if status == reader.OK:
            uid = "-".join("{:02X}".format(b) for b in raw_uid[:4])
            print("Tag detected via IRQ, UID:", uid)
        reader.arm_irq()
        last_arm_ms = ticks_ms()
    elif ticks_diff(ticks_ms(), last_arm_ms) > RETRY_MS:
        reader.arm_irq()
        last_arm_ms = ticks_ms()
    sleep_ms(5)
