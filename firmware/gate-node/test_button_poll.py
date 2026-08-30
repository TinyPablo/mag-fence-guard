# Polls the button every 50ms and prints on every state change, with a
# millisecond timestamp, so bounce behavior and press/release timing can be
# read off the REPL before switching to an interrupt-driven version.

from machine import Pin
from time import sleep_ms, ticks_ms

BUTTON_PIN = 14

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

print("Watching button on GPIO%d. Press it." % BUTTON_PIN)

last_state = button.value()
print("Initial state:", "PRESSED" if last_state == 0 else "released", "at", ticks_ms())

while True:
    print(button.value())
    sleep_ms(20)
