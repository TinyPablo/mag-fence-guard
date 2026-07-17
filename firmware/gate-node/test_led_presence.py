# Onboard LED (GPIO2, common on ESP32 DevKit clones) lights up only when one
# of the 6 known tags (see docs/rfid.md) is near the reader - any other tag
# (e.g. a phone's NFC) leaves it off. Prints every detected UID and whether
# it matched, regardless of the LED, so a bad match/pin can be diagnosed
# from the printed output alone.

from machine import Pin
from time import sleep_ms
from lib.mfrc522 import MFRC522

WHITELIST = {
    "E9-55-91-29",
    "67-2F-3A-CC",
    "3C-EE-5A-4A",
    "6C-0F-2A-49",
    "17-D5-0E-CC",
    "DC-FA-14-4A",
}

reader = MFRC522(sck=18, mosi=23, miso=19, rst=22, cs=5)
led = Pin(2, Pin.OUT)

print("Bring a tag close - LED lights up only for the 6 known tags.")

while True:
    known = False
    status, _ = reader.request(reader.REQIDL)

    if status == reader.OK:
        status, raw_uid = reader.anticoll()
        if status == reader.OK:
            uid = "-".join("{:02X}".format(b) for b in raw_uid[:4])
            known = uid in WHITELIST
            print("UID:", uid, "known:", known)

    led.value(1 if known else 0)
    sleep_ms(150)
