"""A held startup button bypasses the application and leaves the REPL available."""

from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms


MODULE_VERSION = "0.6.1"


def service_requested(role):
    if role == 'gate':
        # Establish the known active-high relay's idle level before app imports.
        Pin(15, Pin.OUT, value=0)
    button = Pin(14, Pin.IN, Pin.PULL_UP)
    print('STARTUP:', role, MODULE_VERSION,
          '- hold GPIO14 to GND for the full 3 seconds for SERVICE mode')
    started = ticks_ms()
    held = button.value() == 0
    while ticks_diff(ticks_ms(), started) < 3000:
        if button.value() != 0:
            held = False
        sleep_ms(20)
    if held and button.value() == 0:
        print('SERVICE MODE - application not started; release the button. REPL is available.')
        return True
    print('Normal startup')
    return False
