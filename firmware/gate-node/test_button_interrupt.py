# Interrupt-driven version of test_button_poll.py: no polling loop, the
# button wakes an IRQ handler on both edges. The onboard LED (GPIO2, same
# pin as test_led_presence.py) mirrors the button state so you can see the
# interrupt firing without needing the REPL open.
#
# The handler itself only timestamps/debounces and flips the LED - it defers
# the print() to micropython.schedule() instead of calling it directly,
# since MicroPython restricts what you can safely do inside a hard IRQ
# (string formatting/printing can trigger a memory allocation, which is not
# allowed there and can crash or silently drop the interrupt).
#
# DEBOUNCE_MS is a starting guess - tune it using what test_button_poll.py
# showed for how long the contact bounces after a press/release.

import micropython
from machine import Pin
from time import ticks_ms, ticks_diff

micropython.alloc_emergency_exception_buf(100)

BUTTON_PIN = 14
LED_PIN = 2
DEBOUNCE_MS = 50

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
led = Pin(LED_PIN, Pin.OUT)

last_irq_ms = 0


def report(arg):
    pressed, when = arg
    print("PRESSED" if pressed else "released", "at", when)


def on_change(pin):
    global last_irq_ms
    now = ticks_ms()
    if ticks_diff(now, last_irq_ms) < DEBOUNCE_MS:
        return
    last_irq_ms = now
    pressed = pin.value() == 0
    led.value(1 if pressed else 0)
    micropython.schedule(report, (pressed, now))


button.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=on_change)

print("Watching button on GPIO%d via interrupt (debounce %dms). Press it." % (BUTTON_PIN, DEBOUNCE_MS))

while True:
    pass
