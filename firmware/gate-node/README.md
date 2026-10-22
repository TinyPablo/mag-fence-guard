# Gate node

ESP32-S3 (N16R8) at the pole: RFID, magnet relay, mic, speaker, button.
Firmware is MicroPython, developed/flashed via Thonny.

## RFID test (`test_rfid.py`)

Prints the UID of any tag brought near the RC522 reader. Upload both
`lib/mfrc522.py` and `test_rfid.py` to the board with Thonny, then run
`test_rfid.py`.

Wiring:

| RC522 pin | ESP32-S3 GPIO |
|---|---|
| SCK | 12 |
| MOSI | 11 |
| MISO | 10 |
| SDA (chip-select) | 17 |
| RST | 16 |
| IRQ | not used - see `docs/rfid.md` for why |
| 3.3V | 3V3 |
| GND | GND |

These pins avoid GPIO22-25 (don't exist on the S3), GPIO19/20 (native USB
D-/D+), and GPIO26-37 (reserved for octal flash/PSRAM on the N16R8 module).

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

## Combined gate controller variants

- `test_gate_unlock.py`: button interrupt and RFID polling every 150 ms;
  RC522 IRQ unconnected.
- `test_gate_unlock_irq.py`: button and RFID interrupts; RC522 IRQ on
  GPIO21, with REQA retried every 200 ms. Preserves the latest reported
  working Thonny variant.

Both use button GPIO14, relay GPIO15, and the RFID SPI wiring above.
Upload `lib/mfrc522.py` alongside the chosen script. Run only one variant
at a time; fully reset the board between comparisons. See
`../../docs/progress.md` for hardware results and unresolved differences.
