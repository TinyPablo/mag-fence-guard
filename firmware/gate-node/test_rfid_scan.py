# Standalone tag scanner - plain SPI polling (same proven approach as
# test_rfid.py), not the IRQ path, to rule that out as a variable while
# re-checking which UID each physical tag actually has. Hold each tag near
# the reader one at a time and copy its printed UID into a new WHITELIST
# (see test_gate_unlock.py / test_led_presence.py for where it's used).
#
# Wiring: SCK=12, MOSI=11, MISO=10, CS=17, RST=16 (same as test_rfid.py).

from time import sleep_ms
from lib.mfrc522 import MFRC522

reader = MFRC522(sck=12, mosi=11, miso=10, rst=16, cs=17)

print("Bring tags near the reader one at a time - UID prints below.")

last_uid = None

while True:
    status, tag_type = reader.request(reader.REQIDL)

    if status == reader.OK:
        status, raw_uid = reader.anticoll()
        if status == reader.OK:
            uid = "-".join("{:02X}".format(b) for b in raw_uid[:4])
            if uid != last_uid:
                print("UID:", uid)
                last_uid = uid
    else:
        last_uid = None

    sleep_ms(200)
