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

## Audio WiFi-relay mic test (`test_audio_wifi_mic.py`)

Records 3s from the INMP441 mic into RAM, then sends the whole clip over
WiFi to a Mac (see `docs/audio.md` and `tools/audio-wifi-relay/`), which
saves it as a `.wav` so it can actually be listened to - a debugging step
to verify the mic module on its own before testing the speaker or a real
ESP32-to-ESP32 link. Recording and sending are separate phases on purpose
- see `docs/audio.md` for why interleaving them produced sped-up audio.
Needs `secrets.py` (copy from `secrets.py.example`, gitignored) uploaded
alongside it.

Wiring:

| INMP441 pin | ESP32 |
|---|---|
| VDD | 3.3V |
| GND | GND |
| L/R | GND (selects left channel) |
| WS | GPIO25 |
| SCK | GPIO26 |
| SD | GPIO33 |
