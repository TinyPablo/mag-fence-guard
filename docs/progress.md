# Hardware progress and test checkpoints

Record hardware results here after each test. Distinguish observed behavior
from behavior expected from the code. Do not record Wi-Fi passwords.

## 2026-10-22 - local gate unlocking confirmed

Board: ESP32-S3 N16R8, running MicroPython through Thonny.
Script: `firmware/gate-node/test_gate_unlock.py`, with
`firmware/gate-node/lib/mfrc522.py` uploaded to the board.

Observed on the connected hardware:

- With the magnet PSU powered and the ESP32 unpowered, the magnet holds.
  The button and RFID do not operate in that state.
- With the ESP32 powered from the Mac over USB and the script started
  manually in Thonny, both an authorized RFID tag and the button unlock
  the magnet.
- `boot.py` is empty. Automatic application startup is not configured;
  previous startup experiments interfered with development access.

The script sets a 3-second unlock interval, polls RFID every 150 ms, and
uses a GPIO interrupt with 50 ms debounce for the button. Its whitelist
contains six tag UIDs. These are code settings; the unlock duration was
not separately measured during this checkpoint.

### Gate control pinout

| Component connection | ESP32-S3 connection |
| --- | --- |
| Button, first contact | GPIO14, internal pull-up |
| Button, other contact | GND |
| Relay IN | GPIO15, active high in the current script |
| RC522 SCK | GPIO12 |
| RC522 MOSI | GPIO11 |
| RC522 MISO | GPIO10 |
| RC522 SDA / CS | GPIO17 |
| RC522 RST | GPIO16 |
| RC522 IRQ | Unconnected |
| RC522 supply | 3V3 and GND |

The magnet circuit uses the relay's COM/NC path: the magnet is powered
while the relay is de-energized. The documented circuit includes a flyback
diode across the magnet. Relay module supply wiring and diode installation
were not independently checked during this checkpoint; record their exact
connections before rebuilding that part of the circuit.

The magnet has its own PSU. At this checkpoint the ESP32 receives power
only from USB, not from the magnet PSU. A standalone ESP32 power path is
still pending.

## Previous audio result - reported on 2026-10-22

Two ESP32 boards previously communicated with microphones and speakers
working on both boards. The hardware was subsequently disconnected for
the gate control tests. The exact firmware revision and network conditions
of that successful audio test have not been re-established.

## Next checkpoint - restore two-board UDP audio

Use `firmware/gate-node/test_audio_udp_duplex.py` on both boards. Upload
each board's own `secrets.py`; keep credentials out of this document.
Disconnect power before changing wiring.

### Audio pinout on each board

| Component connection | ESP32-S3 connection |
| --- | --- |
| INMP441 VDD | 3V3 |
| INMP441 GND and L/R | GND |
| INMP441 WS | GPIO4 |
| INMP441 SCK | GPIO5 |
| INMP441 SD | GPIO6 |
| MAX98357A Vin | 5V |
| MAX98357A GND | GND |
| MAX98357A LRC | GPIO8 |
| MAX98357A BCLK | GPIO7 |
| MAX98357A DIN | GPIO9 |
| MAX98357A SD | 3V3 |
| MAX98357A GAIN | Unconnected |
| Speaker | Amplifier speaker output terminals |

### Test checklist

- Identify the two boards as gate and house; record their actual IPs.
- Check each board's `STATIC_IP`, `PEER_IP`, and `PEER_PORT`. Each board
  needs a different local IP and must target the other board's IP.
- Verify the subnet, gateway, and DNS against the actual LAN. The current
  script hardcodes mask `255.255.255.0` and gateway/DNS `192.168.1.1`.
- Verify that static addresses do not conflict with DHCP leases or other
  devices. The example uses `.237` and `.238`; availability is unverified.
- Start both scripts manually and check received audio in each direction.
  Record sound quality, delay, dropouts, and acoustic feedback separately.
- Repeat after power cycling both boards.

### Repeater test

A Wi-Fi repeater is available with the same SSID as the original access
point and a different BSSID. Its network mode and ESP32 reconnection
behavior have not yet been verified.

- Record which BSSID each board actually connects to, along with its IP.
- Check whether the repeater extends the same LAN or introduces a separate
  subnet, NAT, or client isolation.
- Test audio with both boards near the original access point, then with
  one near the repeater, confirming the actual BSSIDs for each test.
- Check connection selection after restarting a board near the repeater.
- Separately test movement or loss of the original access point; record
  whether reconnection occurs and whether audio resumes. Do not treat a
  successful fresh connection as proof of automatic roaming.

The current audio script connects at startup, assigns a static IP, and
does not explicitly select a BSSID or implement application-level
reconnection handling. Roaming and recovery remain test questions.

## Following stages

1. Add a network command from the house board to unlock the gate, retaining
   local RFID and button control.
2. Integrate audio and unlocking, then add gate-side calling and the
   house-side chime.
3. Prepare standalone ESP32 power and recoverable automatic startup.

HC-SR501 motion sensing is deferred and does not block these stages.
