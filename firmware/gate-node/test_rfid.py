# Quick RFID test: prints the UID of any tag brought near the reader.
# Wiring (RC522 -> ESP32-S3): SCK=12, MOSI=11, MISO=10, SDA(=CS)=17, RST=16,
# IRQ unconnected, 3.3V=3V3, GND=GND. See lib/mfrc522.py for the driver.
#
# These pins were picked to avoid GPIO22-25 (don't exist on the S3),
# GPIO19/20 (native USB D-/D+), GPIO26-37 (reserved for octal flash/PSRAM
# on the N16R8 module), and every pin already used elsewhere in this
# project (2, 4-9, 13, 14, 15, 18).

from time import sleep_ms
from lib.mfrc522 import MFRC522

reader = MFRC522(sck=12, mosi=11, miso=10, rst=16, cs=17)

print("Bring a tag close to the reader...")

last_uid = None

while True:
    status, tag_type = reader.request(reader.REQIDL)

    if status == reader.OK:
        status, raw_uid = reader.anticoll()
        if status == reader.OK:
            uid = "-".join("{:02X}".format(b) for b in raw_uid[:4])
            if uid != last_uid:
                print("Tag detected, UID:", uid)
                last_uid = uid
    else:
        last_uid = None

    sleep_ms(200)
