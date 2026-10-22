# Gate IRQ controller with UDP remote unlocking; audio is not started.
# Preserved hardware checkpoint; see docs/progress.md for test results and
# docs/rfid.md for earlier IRQ behavior. An IRQ does not prove tag presence;
# opening requires a successful UID read and a whitelist match.
#
# Wiring:
#   Button: GPIO14 (pull-up, other leg to GND)
#   Relay: GPIO15 -> relay IN; magnet through COM/NC, flyback diode across magnet
#   RFID: SCK=12, MOSI=11, MISO=10, CS=17, RST=16, IRQ=21

import micropython
from machine import Pin
from time import ticks_ms, ticks_diff, sleep_ms
from lib.mfrc522 import MFRC522
from lib import rfid_debug
from lib.rfid_recovery import Recovery
from lib.remote_link import RemoteLink
from lib.intercom_session import Session
from chime import Chime
from time import ticks_add

micropython.alloc_emergency_exception_buf(100)

BUTTON_PIN = 14
RELAY_PIN = 15
RFID_IRQ_PIN = 21
DEBOUNCE_MS = 50
UNLOCK_MS = 3000
RFID_RETRY_MS = 200
RFID_DIAGNOSTIC_MS = 5000
RFID_RESPONSE_MS = 40
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
rfid_irq = Pin(RFID_IRQ_PIN, Pin.IN, Pin.PULL_UP)
reader = MFRC522(sck=12, mosi=11, miso=10, rst=16, cs=17)


def rfid_status():
    return rfid_debug.status(reader)


def rfid_reset(hardware=False):
    return rfid_debug.reset(reader, hardware)


def rfid_probe(seconds=10):
    return rfid_debug.probe(reader, seconds)


def set_relay(energized):
    relay.value(1 if (energized == RELAY_ACTIVE_HIGH) else 0)


set_relay(False)  # De-energized relay closes NC and powers the magnet.

last_button_irq_ms = 0
unlock_until = 0
unlocked = False
tag_ready = False
call_pressed = False


def report(msg):
    print(msg, "at", ticks_ms())


def on_button(pin):
    global last_button_irq_ms, call_pressed
    now = ticks_ms()
    if pin.value() != 0:
        return
    if ticks_diff(now, last_button_irq_ms) < DEBOUNCE_MS:
        return
    last_button_irq_ms = now
    call_pressed = True


def on_rfid_irq(pin):
    global tag_ready
    tag_ready = True


button.irq(trigger=Pin.IRQ_FALLING, handler=on_button)
rfid_irq.irq(trigger=Pin.IRQ_FALLING, handler=on_rfid_irq)

last_rfid_diagnostic_ms = ticks_ms()
rfid_irq_count = 0
rfid_read_count = 0
rfid_stage = "request"
rfid_cycle_started = ticks_ms()
rfid_stage_started = rfid_cycle_started
rfid_max_service_ms = 0

# A bounded cache covers all retries from the house script (under 2 seconds).
recent_requests = []
link = RemoteLink()
chime = Chime()
session = Session(link, chime, "gate")
recovery = Recovery(reader)
reader.arm_irq()
rfid_cycle_started = ticks_ms()
rfid_stage_started = rfid_cycle_started


def handle_call():
    global call_pressed
    if call_pressed:
        call_pressed = False
        session.call()
    session.poll()


def handle_remote():
    global unlock_until, unlocked
    link.poll()
    # Bound work per loop so network traffic cannot starve local control.
    for _ in range(4):
        packet = link.receive()
        if packet is None:
            break
        session.receive(packet)
        if not packet.startswith(b"OPEN "):
            continue
        request_id = packet[5:]
        if len(request_id) != 24 or any(c not in b"0123456789abcdef" for c in request_id):
            continue
        now = ticks_ms()
        recent_requests[:] = [(key, at) for key, at in recent_requests
                              if ticks_diff(now, at) < 10000]
        if any(key == request_id for key, _ in recent_requests):
            link.send(b"ACK " + request_id)
            continue
        if len(recent_requests) >= 32:
            continue
        unlock_until = ticks_add(now, UNLOCK_MS)
        set_relay(True)
        unlocked = True
        recent_requests.append((request_id, now))
        print("UNLOCKED remote:", request_id.decode())
        link.send(b"ACK " + request_id)


print("Gate control ready - call button GPIO%d, RFID IRQ GPIO%d, relay GPIO%d." % (BUTTON_PIN, RFID_IRQ_PIN, RELAY_PIN))

try:
    while True:
        handle_remote()
        handle_call()
        chime.poll()
        now = ticks_ms()

        # IRQ is a hint only: inspect RxIRq, never run blocking anticoll()
        # merely because the GPIO fired. Both exchanges advance across loops.
        service_started = ticks_ms()
        if recovery.poll():
            rfid_stage = "recovery"
            tag_ready = False
        else:
            if rfid_stage == "recovery":
                tag_ready = False
                reader.arm_irq()
                rfid_stage = "request"
                rfid_cycle_started = ticks_ms()
                rfid_stage_started = rfid_cycle_started
            if tag_ready:
                rfid_irq_count += 1
                tag_ready = False
            if rfid_stage in ("request", "uid"):
                if reader.irq_received():
                    if rfid_stage == "request":
                        reader.start_anticoll_irq()
                        rfid_stage = "uid"
                        rfid_stage_started = ticks_ms()
                    else:
                        status, raw_uid = reader.finish_anticoll_irq()
                        reader.disarm_irq()
                        rfid_stage = "wait"
                        if status == reader.OK:
                            rfid_read_count += 1
                            uid = "-".join("{:02X}".format(b) for b in raw_uid[:4])
                            known = uid in WHITELIST
                            print("Tag UID:", uid, "known:", known)
                            if known:
                                unlock_until = ticks_add(ticks_ms(), UNLOCK_MS)
                elif ticks_diff(now, rfid_stage_started) >= RFID_RESPONSE_MS:
                    reader.disarm_irq()
                    rfid_stage = "wait"
            if rfid_stage == "wait" and ticks_diff(now, rfid_cycle_started) >= RFID_RETRY_MS:
                reader.arm_irq()
                rfid_stage = "request"
                rfid_cycle_started = ticks_ms()
                rfid_stage_started = rfid_cycle_started
        rfid_max_service_ms = max(rfid_max_service_ms,
                                  ticks_diff(ticks_ms(), service_started))

        if ticks_diff(now, last_rfid_diagnostic_ms) >= RFID_DIAGNOSTIC_MS:
            print("RFID diagnostic: IRQ=%d reads=%d pin=%d flags=0x%02X stage=%s max_ms=%d resets=%d restored=%d failures=%d" %
                  (rfid_irq_count, rfid_read_count, rfid_irq.value(),
                   reader._rreg(0x04), rfid_stage, rfid_max_service_ms,
                   recovery.attempts, recovery.restored, recovery.failures))
            last_rfid_diagnostic_ms = now
            rfid_max_service_ms = 0

        should_unlock = ticks_diff(unlock_until, now) > 0
        if should_unlock != unlocked:
            unlocked = should_unlock
            set_relay(unlocked)
            print("UNLOCKED" if unlocked else "LOCKED", "at", now)

        sleep_ms(5)
finally:
    button.irq(handler=None)
    rfid_irq.irq(handler=None)
    set_relay(False)
    chime.close()
    link.close()
