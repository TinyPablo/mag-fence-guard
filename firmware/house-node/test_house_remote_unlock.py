# House button: GPIO14 to GND. Upload lib/remote_link.py and this board's
# secrets.py as well. Run manually in Thonny; microphone streaming is not started.

import os
from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms
from lib.remote_link import RemoteLink
from chime import Chime

button = Pin(14, Pin.IN, Pin.PULL_UP)
chime = Chime()
link = RemoteLink()
recent_calls = []
DEBOUNCE_MS = 50
RETRY_MS = 500
MAX_ATTEMPTS = 4
pending = None
attempts = 0
last_send = 0
raw_state = button.value()
stable_state = raw_state
changed_at = ticks_ms()

print("House ready - button GPIO14; control UDP port 5007")
try:
    while True:
        link.poll()
        chime.poll()
        now = ticks_ms()
        state = button.value()
        if state != raw_state:
            raw_state = state
            changed_at = now
        if state != stable_state and ticks_diff(now, changed_at) >= DEBOUNCE_MS:
            stable_state = state
            if state == 0:
                if pending is not None:
                    print("Request still pending; press ignored")
                elif not link.wlan.isconnected():
                    print("No WiFi; press again after connection")
                else:
                    # A fresh random ID prevents collisions across board restarts.
                    pending = os.urandom(12).hex().encode()
                    attempts = 0
                    print("Unlock requested:", pending.decode())

        for _ in range(4):
            packet = link.receive()
            if packet is None:
                break
            if packet.startswith(b"CALL "):
                call_id = packet[5:]
                if len(call_id) != 24 or any(c not in b"0123456789abcdef" for c in call_id):
                    continue
                recent_calls[:] = [(key, at) for key, at in recent_calls
                                   if ticks_diff(now, at) < 10000]
                if not any(key == call_id for key, _ in recent_calls):
                    if len(recent_calls) >= 32:
                        continue
                    recent_calls.append((call_id, now))
                    chime.ring()
                    print("Gate call - ringing:", call_id.decode())
                link.send(b"RING_ACK " + call_id)
            if pending is not None and packet == b"ACK " + pending:
                print("Gate confirmed unlock:", pending.decode())
                pending = None

        if pending is not None and (attempts == 0 or ticks_diff(now, last_send) >= RETRY_MS):
            if attempts >= MAX_ATTEMPTS:
                print("No confirmation; gate state unknown:", pending.decode())
                pending = None
            else:
                link.send(b"OPEN " + pending)
                attempts += 1
                last_send = now
        sleep_ms(5)
finally:
    chime.close()
    link.close()
