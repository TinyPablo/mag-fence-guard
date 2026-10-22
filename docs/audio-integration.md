# Integrated two-way voice test

Voice is enabled only in TALKING. Gate calling, house answer/hangup and
house opening retain their existing buttons. The original standalone UDP
duplex test remains unchanged.

## Uploads

On BOTH boards upload:

- `firmware/gate-node/lib/intercom_audio.py` as `/lib/intercom_audio.py`.
- Updated `firmware/gate-node/lib/intercom_session.py` as `/lib/intercom_session.py`.
- Updated `firmware/house-node/chime.py` as `/chime.py`.

Upload updated `test_gate_remote_unlock.py` to the gate and updated
`test_house_remote_unlock.py` to the house. Retain the existing gate RFID
modules, both copies of `lib/remote_link.py`, and per-board `secrets.py`.
`PEER_PORT` must be the same on both boards (existing audio value 5006),
different from control port 5007. Keep distinct static IPs, reciprocal peer
IPs and the previously tested SOURCE settings. Restart both boards before
running. Do not run the standalone audio test simultaneously.

Both boards need INMP441 VDD=3V3, GND/LR=GND, SCK5/WS4/SD6;
MAX98357A Vin=5V, GND, BCLK7/LRC8/DIN9, SD=3V3, GAIN floating, speaker
between amplifier outputs. Gate RFID IRQ remains GPIO21. House open is
GPIO14; answer/hangup is GPIO18. Use the existing USB power arrangement.

## Operation and implementation

RINGING plays the chime, without allocating or starting a microphone.
On TALKING, chime releases I2S1; voice initializes microphone I2S0 and speaker
I2S1. Both directions use 16 kHz mono PCM, converting microphone 32-bit
samples to 16-bit, with 256 samples per packet. I2S callbacks make reads and
writes nonblocking. Buffers stay alive until their callbacks complete;
there is at most one pending microphone read and one speaker write.

Packets include the current 24-byte call ID and a wrapping 16-bit sequence
number. Peer address, exact packet length, session ID and sequence order
are checked. At most four datagrams are drained per loop; latest received
PCM replaces pending playback instead of building an unbounded queue.
This favors low latency and can drop chunks under load. Socket recvfrom
allocates a bounded packet per receive; native microphone/speaker buffers
are 8192/4096 bytes. There is no codec, jitter buffer or acoustic echo
cancellation in this test.

House hangup/opening, session timeout and control heartbeat loss stop voice,
deinitialize the microphone and speaker, close the audio socket, and restore
the chime's speaker. A detected local Wi-Fi disconnect stops voice too.
Transient UDP send errors are counted and dropped. Fatal initialization or
receive errors end the local call; peer control timeout provides fallback.
Five-second VOICE counters report sent, received, replaced playback chunks,
and send errors. Existing RFID recovery can still interrupt servicing and
is not fixed by this integration. Repeated hardware stability is unverified.

## Hardware checklist

1. Gate press: both chimes, no VOICE started message and no microphone audio.
2. House GPIO18: TALKING then VOICE started on both consoles. Speak at each
   microphone separately and confirm the opposite speaker. Separate boards
   physically to reduce feedback.
3. GPIO18 again: VOICE stopped on both; microphone sound no longer passes.
4. Repeat call/answer/hangup at least five times, checking no startup/resource
   errors and no stale audio from the previous call.
5. House GPIO14 during TALKING: gate opens and audio ends on both sides.
6. Scan/remove RFID during TALKING, test gate call-button handling, and
   inspect recovery counters and audio quality.
7. Stop a board during TALKING: the other should stop audio after the control
   heartbeat timeout (approximately 3 seconds). Restart and make a new call.

Host-side checks: `python3 -m unittest discover -s tests -v`.
These mock transport/I2S; they do not verify timing or sound on ESP32.
