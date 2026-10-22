# Gate unlocking with interrupt-driven button and RFID, plus 200 ms REQA retries.
# Preserved hardware checkpoint; see docs/progress.md for test results and
# docs/rfid.md for earlier IRQ behavior. An IRQ does not prove tag presence;
# opening requires a successful UID read and a whitelist match.
#
# Wiring:
#   Button: GPIO14 (pull-up, other leg to GND)
#   Relay: GPIO15 -> relay IN; magnet through COM/NC, flyback diode across magnet
#   RFID: SCK=12, MOSI=11, MISO=10, CS=17, RST=16, IRQ=21

import micropython
from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms
from lib.mfrc522 import MFRC522

micropython.alloc_emergency_exception_buf(100)

BUTTON_PIN = 14
RELAY_PIN = 15
RFID_IRQ_PIN = 21
DEBOUNCE_MS = 50
UNLOCK_MS = 3000
RFID_RETRY_MS = 200
RELAY_ACTIVE_HIGH = True

WHITELIST = {
    "E9-55-91-29",
    "67-2F-3A-CC",
    "3C-EE-5A-4A",
    "6C-0F-2A-49",
    "17-D5-0E-CC",
    "DC-FA-14-4A",
}

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
relay = Pin(RELAY_PIN, Pin.OUT)
rfid_irq = Pin(RFID_IRQ_PIN, Pin.IN, Pin.PULL_UP)
reader = MFRC522(sck=12, mosi=11, miso=10, rst=16, cs=17)


def set_relay(energized):
    relay.value(1 if (energized == RELAY_ACTIVE_HIGH) else 0)


set_relay(False)  # De-energized relay closes NC and powers the magnet.

last_button_irq_ms = 0
unlock_until = 0
unlocked = False
tag_ready = False


def report(msg):
    print(msg, "at", ticks_ms())


def on_button(pin):
    global last_button_irq_ms, unlock_until
    now = ticks_ms()
    if pin.value() != 0:
        return
    if ticks_diff(now, last_button_irq_ms) < DEBOUNCE_MS:
        return
    last_button_irq_ms = now
    unlock_until = ticks_ms() + UNLOCK_MS
    micropython.schedule(report, "button pressed, unlocking")


def on_rfid_irq(pin):
    global tag_ready
    tag_ready = True


button.irq(trigger=Pin.IRQ_FALLING, handler=on_button)
rfid_irq.irq(trigger=Pin.IRQ_FALLING, handler=on_rfid_irq)

reader.arm_irq()
last_rfid_arm_ms = ticks_ms()

print("Gate control ready - button GPIO%d, RFID IRQ GPIO%d, relay GPIO%d." % (BUTTON_PIN, RFID_IRQ_PIN, RELAY_PIN))

while True:
    now = ticks_ms()

    if tag_ready:
        tag_ready = False
        reader.disarm_irq()
        status, raw_uid = reader.anticoll()
        if status == reader.OK:
            uid = "-".join("{:02X}".format(b) for b in raw_uid[:4])
            known = uid in WHITELIST
            print("Tag UID:", uid, "known:", known)
            if known:
                unlock_until = ticks_ms() + UNLOCK_MS
        reader.arm_irq()
        last_rfid_arm_ms = ticks_ms()
    elif ticks_diff(now, last_rfid_arm_ms) > RFID_RETRY_MS:
        reader.arm_irq()
        last_rfid_arm_ms = now

    should_unlock = ticks_diff(unlock_until, now) > 0
    if should_unlock != unlocked:
        unlocked = should_unlock
        set_relay(unlocked)
        print("UNLOCKED" if unlocked else "LOCKED", "at", now)

    sleep_ms(5)
