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
