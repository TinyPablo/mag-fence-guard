# House button: GPIO14 to GND. Upload lib/remote_link.py and this board's
# secrets.py as well. Run manually in Thonny; voice runs only while TALKING.

from lib.firmware_info import report

SCRIPT_VERSION = "0.4.0"
print("FIRMWARE starting: role=house version=" + SCRIPT_VERSION)

import os
from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms
from lib.remote_link import RemoteLink
from chime import Chime
from lib.intercom_session import Session
from lib.intercom_audio import Voice

report("house", SCRIPT_VERSION)

button = Pin(14, Pin.IN, Pin.PULL_UP)
chime = Chime()
link = RemoteLink()
session = Session(link, chime, "house")
voice = Voice(chime, "house")
session.voice = voice
talk_button = Pin(18, Pin.IN, Pin.PULL_UP)
talk_raw = talk_button.value()
talk_stable = talk_raw
talk_changed = ticks_ms()
DEBOUNCE_MS = 50
RETRY_MS = 500
MAX_ATTEMPTS = 4
pending = None
attempts = 0
last_send = 0
raw_state = button.value()
stable_state = raw_state
changed_at = ticks_ms()

print("House ready - open GPIO14, talk GPIO18; control UDP port 5007")
try:
    while True:
        link.poll()
        chime.poll()
        now = ticks_ms()
        talk_state = talk_button.value()
        if talk_state != talk_raw:
            talk_raw = talk_state
            talk_changed = now
        if talk_state != talk_stable and ticks_diff(now, talk_changed) >= DEBOUNCE_MS:
            talk_stable = talk_state
            if talk_state == 0:
                session.talk_button()
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
                    session.end()
                    pending = os.urandom(12).hex().encode()
                    attempts = 0
                    print("Unlock requested:", pending.decode())

        for _ in range(4):
            packet = link.receive()
            if packet is None:
                break
            session.receive(packet)
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
        session.poll()
        voice.service(session)
        sleep_ms(2)
finally:
    voice.stop()
    chime.close()
    link.close()
