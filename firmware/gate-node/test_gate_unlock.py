# Combines the interrupt-driven button (test_button_magnet.py) with
# polling RFID (test_rfid_scan.py) into one control loop: either a button
# press or one of the 6 whitelisted tags unlocks the magnet for UNLOCK_MS.
#
# RFID stays on plain SPI polling, not IRQ - test_rfid_irq_diag.py showed
# the reader's IRQ pin fires on TxIRq/LoAlertIRq (its own transmission
# completing) even with those sources masked off in ComIEnReg, not just on
# a real RxIRq tag response. That's a clone-chip quirk, not fixable from
# the host side - same conclusion as the original attempt documented in
# docs/rfid.md. At human-paced access (tag held ~1s), 150ms polling
# latency doesn't matter, so this isn't a real loss.
#
# Every unlock path (button, RFID, and later a remote/cloud command) is
# meant to go through the single unlock(source) function below, not have
# its own separate "open the relay" logic - that way logging (added later,
# once the cloud/logging side exists) only needs to be wired up once and
# automatically covers every trigger, local or remote, instead of being
# something that has to be remembered per source.
#
# Wiring:
#   Button: GPIO14 (pull-up, other leg to GND)
#   Relay:  GPIO15 -> relay IN; magnet wired through the relay's NC contact
#           (see test_button_magnet.py notes - locked by default, no signal
#           needed to stay locked, flyback diode across the magnet)
#   RFID:   SCK=12, MOSI=11, MISO=10, CS=17, RST=16 (IRQ pin unconnected)

import micropython
from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms
from lib.mfrc522 import MFRC522

micropython.alloc_emergency_exception_buf(100)

BUTTON_PIN = 14
RELAY_PIN = 15
DEBOUNCE_MS = 50
UNLOCK_MS = 3000
RFID_POLL_MS = 150
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
reader = MFRC522(sck=12, mosi=11, miso=10, rst=16, cs=17)


def set_relay(energized):
    relay.value(1 if (energized == RELAY_ACTIVE_HIGH) else 0)


set_relay(False)  # boot state: de-energized -> NC closed -> magnet powered -> locked

last_button_irq_ms = 0
last_rfid_uid = None
unlock_until = 0
unlocked = False


def unlock(source):
    global unlock_until
    unlock_until = ticks_ms() + UNLOCK_MS
    micropython.schedule(report, source)


def report(source):
    print("unlock:", source, "at", ticks_ms())


def on_button(pin):
    global last_button_irq_ms
    now = ticks_ms()
    if pin.value() != 0:
        return  # only react to the press (falling) edge, not the release
    if ticks_diff(now, last_button_irq_ms) < DEBOUNCE_MS:
        return
    last_button_irq_ms = now
    unlock("button")


button.irq(trigger=Pin.IRQ_FALLING, handler=on_button)

print("Gate control ready - button GPIO%d (IRQ), RFID polling, relay GPIO%d." % (BUTTON_PIN, RELAY_PIN))

last_rfid_poll_ms = 0

while True:
    now = ticks_ms()

    if ticks_diff(now, last_rfid_poll_ms) >= RFID_POLL_MS:
        last_rfid_poll_ms = now
        status, _ = reader.request(reader.REQIDL)
        if status == reader.OK:
            status, raw_uid = reader.anticoll()
            if status == reader.OK:
                uid = "-".join("{:02X}".format(b) for b in raw_uid[:4])
                if uid != last_rfid_uid:
                    known = uid in WHITELIST
                    print("Tag UID:", uid, "known:", known)
                    if known:
                        unlock("rfid:" + uid)
                last_rfid_uid = uid
        else:
            last_rfid_uid = None

    should_unlock = ticks_diff(unlock_until, now) > 0
    if should_unlock != unlocked:
        unlocked = should_unlock
        set_relay(unlocked)
        print("UNLOCKED" if unlocked else "LOCKED", "at", now)

    sleep_ms(5)
