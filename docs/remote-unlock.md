# Remote unlock bench test

Audio is not started by these scripts. Both ESP32 boards use USB power;
retain the previously tested magnet PSU and relay wiring. Startup remains
manual in Thonny.

## Files to upload

| Board | Files on the board |
| --- | --- |
| Gate | `test_gate_remote_unlock.py`, `lib/mfrc522.py`, `lib/remote_link.py`, `secrets.py` |
| House | `test_house_remote_unlock.py`, `lib/remote_link.py`, `secrets.py` |

The shared `lib/remote_link.py` source is in `firmware/gate-node/lib/`;
upload the same file to a `lib` directory on each board. The house script
source is in `firmware/house-node/`. Gate sources are in
`firmware/gate-node/`.

Each board needs its own `secrets.py`, based on the existing example:
`WIFI_SSID`, `WIFI_PASSWORD`, `STATIC_IP`, `PEER_IP`, and `SOURCE`.
Use different static IPs and reciprocal peer IPs; retain the previously
working audio addresses. Set `SOURCE = "ap"` for the repeater and
`SOURCE = "router"` for the router. Control uses fixed UDP port 5007;
`PEER_PORT` remains the audio setting and is not used here. Both nodes
currently use mask `255.255.255.0` and gateway/DNS `192.168.1.1`.

## Wiring

Gate wiring matches `test_gate_unlock_irq.py`: button GPIO14 to GND,
relay IN GPIO15, RC522 SCK12/MOSI11/MISO10/CS17/RST16/IRQ21,
RC522 power 3V3 and GND. Preserve the tested relay supply, COM/NC magnet
circuit, and flyback diode. The house button connects GPIO14 to GND.
Microphones and amplifiers can remain connected but are not used.

## Behavior

Start the gate script and then the house script. Wi-Fi connections are
pinned to the configured BSSID. Connection attempts run without waiting
in the local control loop; the gate button and RFID remain serviced while
Wi-Fi is unavailable. Wi-Fi setup or firmware/driver initialization errors
can still prevent startup and are printed by Thonny.

The house button is debounced in its main loop. A new press sends a random
request ID, with at most four attempts 500 ms apart. Presses while a request
is pending are ignored. A press without Wi-Fi is not queued for later.
The gate activates the relay for 3 seconds and acknowledges the request.
A confirmation means the software commanded the relay; no physical lock
position sensor is installed. No confirmation means the result is unknown.

The gate remembers up to 32 request IDs for 10 seconds. A retry receives
another acknowledgement without extending the unlock interval. This
memory does not survive a gate restart. Distinct requests extend the
unlock interval. UDP packets are accepted only from the configured peer IP
and port; the bench protocol has no cryptographic authentication and is
intended for the existing trusted LAN test.

## Hardware verification

- Confirm gate RFID and the gate button before starting the house script.
- Press the house button once: verify physical release and automatic
  relocking, plus a matching request/confirmation in the two consoles.
- Test each direction of the router/repeater assignment if needed.
- Try repeated presses and holding the button; check the reported behavior.
- Disconnect the house board; confirm gate RFID and button still work.
- Interrupt the selected Wi-Fi point; confirm local gate operation, then
  restore it and test a new house press after reconnection.
- Stop and restart each script. Check relay state and retry behavior.

The scripts have not yet been verified on the ESP32 hardware.

## Gate calling extension

The latest remote scripts replace the gate button's temporary unlock
function with calling the house. Upload the updated gate and house scripts,
plus `firmware/house-node/chime.py` to `/chime.py` on the house board.
The house amplifier uses the existing audio wiring: Vin 5V, GND, BCLK GPIO7,
LRC GPIO8, DIN GPIO9, SD 3V3, GAIN unconnected, speaker on amplifier outputs.
Do not run the duplex audio script at the same time: both use I2S1.

A gate press sends `CALL <id>`; the house starts a two-tone chime and sends
`RING_ACK <id>`. Duplicate packets are acknowledged without replaying the
chime. A new call can restart a playing chime. The gate applies a one-second
cooldown and up to four attempts 500 ms apart. The confirmation reports
software acceptance, not measured speaker output. The house button still
sends `OPEN`; RFID still unlocks locally. The preceding checklist's local
button-unlock expectation applies only to the initial version.

Verify a gate press rings the house without releasing the magnet, a house
press opens the gate during/after ringing, RFID still opens, and a held gate
button does not continuously ring. Then test a disconnected house: gate
presses must not release the lock and RFID must remain operational.

## Call-state control test (current version)

Upload updated `test_gate_remote_unlock.py` to the gate and
`test_house_remote_unlock.py` to the house. Upload the same
`firmware/gate-node/lib/intercom_session.py` to `/lib/intercom_session.py`
on BOTH boards. Upload updated `firmware/house-node/chime.py` to `/chime.py`
on BOTH boards. Keep `/lib/remote_link.py`, gate `/lib/mfrc522.py`, and each
board's existing `/secrets.py`. Restart both boards before running.

House: open button GPIO14 to GND; talk button GPIO18 to GND. The gate now
needs its speaker/amplifier connected with the same I2S pinout as the house
(BCLK7/LRC8/DIN9). Microphones remain unused on both boards. No LED is
required for this test; inspect `CALL STATE` logs in both Thonny consoles.

1. Gate press: both speakers chime; both logs reach RINGING. Magnet holds.
2. House GPIO18 press: both logs reach TALKING. There is no voice audio yet.
3. House GPIO18 again: both logs reach IDLE. Another press in IDLE is ignored.
4. Make a new call and press house GPIO14 without answering: gate opens for
   3 seconds and both sessions end. Repeat while TALKING.
5. Leave a call unanswered: it ends after 30 seconds. Hold or repeat the
   gate button during an active call: it must not restart ringing.
6. Confirm RFID still unlocks. Stop one script during a call: the other
   returns to IDLE after about 3 seconds. Restart and initiate a new call.

The house open button is still usable in IDLE. Session heartbeats and
revision ordering replace the preceding RING_ACK-only exchange. A call
acceptance triggers each chime once; new microphone audio and audible
answer/end signals are not implemented in this stage.

## RFID polling wiring update

The latest integrated gate script no longer uses reader IRQ. Disconnect
RC522 IRQ from GPIO21 with power off. SPI SCK12/MOSI11/MISO10/CS17/RST16,
3V3/GND and the other components stay unchanged. Upload the updated driver
and gate script together. Earlier IRQ wiring instructions above refer to
previous checkpoints. Startup now explicitly reports `RFID polling (no IRQ)`.
Keep the recovery/debug/session modules on the board.

## Current wiring: IRQ restored after unsuccessful polling trial

The preceding polling update was reverted. Reconnect RC522 IRQ to GPIO21
with power removed and upload the restored driver and gate script together.
Keep the existing recovery, debug, session and chime modules. House wiring
and code remain unchanged. Current startup reports `RFID IRQ GPIO21`.
