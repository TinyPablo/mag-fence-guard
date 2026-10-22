# Run one MODE at a time, restarting the board between comparisons.
# GPIO14 button triggers only the selected load. Tags never unlock here.
# Existing wiring: relay IN15, RFID SCK12/MOSI11/MISO10/CS17/RST16/IRQ21.

import network
from machine import Pin
from time import ticks_ms, ticks_diff, ticks_add, sleep_ms
from lib.mfrc522 import MFRC522
from lib.rfid_recovery import Recovery
from lib import rfid_debug

MODE = "rfid"  # "rfid", "chime", or "relay"
WIFI_ENABLED = True  # Keep the same Wi-Fi load in all three comparisons.

if MODE not in ("rfid", "chime", "relay"):
    raise ValueError("MODE must be rfid, chime, or relay")

# Initialize the relay before any peripheral initialization can fail.
relay = Pin(15, Pin.OUT, value=0)  # Existing active-high module, COM/NC wiring.
button = Pin(14, Pin.IN, Pin.PULL_UP)
reader = None
chime = None
link = None

try:
    if WIFI_ENABLED:
        from lib.remote_link import RemoteLink
        link = RemoteLink()
    else:
        network.WLAN(network.STA_IF).active(False)
    if MODE == "chime":
        from chime import Chime
        chime = Chime()
    reader = MFRC522(sck=12, mosi=11, miso=10, rst=16, cs=17)
    check = Recovery(reader)
    # Use only mismatch(); never call Recovery.poll() in this diagnostic.
    rfid_debug.status(reader)
    reader.arm_irq()
    started = ticks_ms()
    cycle = stage_at = last_check = last_report = started
    stage = "request"
    reads = 0
    raw = stable = button.value()
    changed = started
    relay_until = None
    print("ISOLATION MODE:", MODE, "WiFi:", WIFI_ENABLED)
    print("Tags only print UIDs. Button GPIO14 triggers the selected load.")
    while True:
        now = ticks_ms()
        if link is not None:
            link.poll()
            # Drain a bounded number; remote commands never operate the relay.
            for _ in range(4):
                if link.receive() is None:
                    break
        if chime is not None:
            chime.poll()
        state = button.value()
        if state != raw:
            raw = state
            changed = now
        if state != stable and ticks_diff(now, changed) >= 50:
            stable = state
            if state == 0:
                print("LOAD TRIGGER:", MODE, "at", now)
                if MODE == "chime":
                    chime.ring()
                elif MODE == "relay":
                    relay.value(1)
                    relay_until = ticks_add(now, 3000)
        if relay_until is not None and ticks_diff(now, relay_until) >= 0:
            relay.value(0)
            relay_until = None
            print("Relay returned to locked state at", now)

        if stage in ("request", "uid"):
            if reader.irq_received():
                if stage == "request":
                    reader.start_anticoll_irq()
                    stage = "uid"
                    stage_at = ticks_ms()
                else:
                    code, uid = reader.finish_anticoll_irq()
                    if code == reader.OK:
                        reads += 1
                        print("UID:", "-".join("%02X" % b for b in uid[:4]))
                    reader.disarm_irq()
                    stage = "wait"
            elif ticks_diff(now, stage_at) >= 40:
                reader.disarm_irq()
                stage = "wait"
        if stage == "wait" and ticks_diff(now, cycle) >= 200:
            reader.arm_irq()
            stage = "request"
            cycle = stage_at = ticks_ms()
        if ticks_diff(now, last_check) >= 1000:
            last_check = now
            reason = check.mismatch()
            if reason:
                print("CONFIG LOST: mode=%s uptime_ms=%d reads=%d %s" %
                      (MODE, ticks_diff(now, started), reads, reason))
                rfid_debug.status(reader)
                print("Test stopped without resetting the reader.")
                break
        if ticks_diff(now, last_report) >= 5000:
            last_report = now
            print("ISOLATION: mode=%s uptime_ms=%d reads=%d stage=%s" %
                  (MODE, ticks_diff(now, started), reads, stage))
        sleep_ms(5)
finally:
    relay.value(0)
    if reader is not None:
        reader.disarm_irq()
    if chime is not None:
        chime.close()
    if link is not None:
        link.close()
