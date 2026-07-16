# Quick RFID test: prints the UID of any tag brought near the reader.
# Wiring (RC522 -> ESP32): SCK=18, MOSI=23, MISO=19, SDA(=CS)=5, RST=22,
# IRQ unconnected, 3.3V=3V3, GND=GND. See lib/mfrc522.py for the driver.

from time import sleep_ms
from lib.mfrc522 import MFRC522

reader = MFRC522(sck=18, mosi=23, miso=19, rst=22, cs=5)

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
