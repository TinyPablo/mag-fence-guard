from machine import Pin
from time import sleep, ticks_ms, ticks_diff

pir = Pin(13, Pin.IN)
previous = pir.value()
high_since = ticks_ms() if previous else None

# 10 minutes * 60 seconds / 0.2 seconds = 3000 iterations
for i in range(3000):
    state = pir.value()

    if state == 1 and previous == 0:
        high_since = ticks_ms()

    if state == 0 and previous == 1:
        duration = ticks_diff(ticks_ms(), high_since) / 1000
        print("KONIEC - sygnał HIGH trwał %.1f s" % duration)
        high_since = None

    # Calculate time in seconds
    seconds = i * 0.2
    m, s = divmod(seconds, 60)
    
    prefix = "WAIT" if seconds < 60 else ""
    print("%dm %02ds %s OUT=%d" % (m, s, prefix, state))

    previous = state
    sleep(0.2)
