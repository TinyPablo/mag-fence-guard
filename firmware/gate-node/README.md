# Gate node

ESP32 (ESP32-WROOM-32 DevKit) at the pole: RFID, magnet relay, mic, speaker,
button. Firmware is MicroPython, developed/flashed via Thonny.

## RFID test (`test_rfid.py`)

Prints the UID of any tag brought near the RC522 reader. Upload both
`lib/mfrc522.py` and `test_rfid.py` to the board with Thonny, then run
`test_rfid.py`.

Wiring:

| RC522 pin | ESP32 GPIO |
|---|---|
| SCK | 18 |
| MOSI | 23 |
| MISO | 19 |
| SDA (chip-select) | 5 |
| RST | 22 |
| IRQ | not used - see `docs/rfid.md` for why |
| 3.3V | 3V3 |
| GND | GND |

`lib/mfrc522.py` is vendored from
[wendlers/micropython-mfrc522](https://github.com/wendlers/micropython-mfrc522)
(MIT License) with an added `esp32` branch in `__init__` - the original only
targeted WiPy/LoPy/FiPy/esp8266.

## LED + whitelist test (`test_led_presence.py`)

Same wiring as above. Lights the onboard ESP32 LED (GPIO2) only for one of
the 6 known tags (see `docs/rfid.md`), and prints every detected UID plus
whether it matched, so a mismatch can be diagnosed from the printed output.
Detection is plain SPI polling - the IRQ pin was tried and dropped, see
`docs/rfid.md`.
