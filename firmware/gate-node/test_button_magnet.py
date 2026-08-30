# Electromagnet control via relay: the magnet is powered (locked) by
# default, wired through the relay's NC contact (see wiring notes) - so the
# relay only needs to be energized for the ~3s unlock window, and a
# firmware crash/reset leaves the gate locked, not open. Button press is
# interrupt-driven (see test_button_interrupt.py), not polled.
#
# RELAY_ACTIVE_HIGH: test this on the bench with the magnet DISCONNECTED
# first. Set it to True, run, press the button, and check whether the
# relay actually clicks/energizes on press (listen for the click, or probe
# continuity on COM-NC). If it's backwards (energizes when idle, releases
# on press), flip this to False.

import micropython
from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms

micropython.alloc_emergency_exception_buf(100)

BUTTON_PIN = 14
RELAY_PIN = 15
DEBOUNCE_MS = 50
UNLOCK_MS = 3000
RELAY_ACTIVE_HIGH = True

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
relay = Pin(RELAY_PIN, Pin.OUT)


def set_relay(energized):
    relay.value(1 if (energized == RELAY_ACTIVE_HIGH) else 0)


set_relay(False)  # boot state: de-energized -> NC closed -> magnet powered -> locked

last_irq_ms = 0
unlock_until = 0
unlocked = False


def report(msg):
    print(msg, "at", ticks_ms())


def on_press(pin):
    global last_irq_ms, unlock_until
    now = ticks_ms()
    if pin.value() != 0:
        return  # only react to the press (falling) edge, not the release
    if ticks_diff(now, last_irq_ms) < DEBOUNCE_MS:
        return
    last_irq_ms = now
    unlock_until = ticks_ms() + UNLOCK_MS
    micropython.schedule(report, "button pressed, unlocking")


button.irq(trigger=Pin.IRQ_FALLING, handler=on_press)

print("Button GPIO%d, relay GPIO%d. Press to unlock for %dms." % (BUTTON_PIN, RELAY_PIN, UNLOCK_MS))

while True:
    now = ticks_ms()
    should_unlock = ticks_diff(unlock_until, now) > 0
    if should_unlock != unlocked:
        unlocked = should_unlock
        set_relay(unlocked)
        print("UNLOCKED" if unlocked else "LOCKED", "at", now)
    sleep_ms(50)
