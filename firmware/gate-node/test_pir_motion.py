# Prints a line every time the HC-SR501 PIR OUT pin changes state, with a
# millisecond timestamp so trigger/hold timing can be read off the REPL
# (useful for tuning the sensitivity/distance and time-delay potentiometers).

from machine import Pin
from time import sleep_ms, ticks_ms

pir = Pin(13, Pin.IN)

print("Watching PIR on GPIO13. Move in front of the sensor.")

last_state = pir.value()
print("Initial state:", "MOTION" if last_state else "idle", "at", ticks_ms())

while True:
    state = pir.value()
    if state != last_state:
        print("MOTION" if state else "idle", "at", ticks_ms())
        last_state = state
    sleep_ms(20)
