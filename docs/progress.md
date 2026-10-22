# Hardware progress and test checkpoints

Record hardware results here after each test. Distinguish observed behavior
from behavior expected from the code. Do not record Wi-Fi passwords.

## Current implementation - integrated voice awaiting hardware verification

Two-way audio has been added to the existing call scripts, only while
TALKING. This is not yet a hardware-confirmed checkpoint. See
`audio-integration.md` for upload paths and acceptance checks. The following
checkpoint describes the last tested behavior before this addition.

## Current checkpoint - call controls with recoverable IRQ RFID

This section supersedes earlier pending-test notes below. The dated entries
retain the sequence of experiments.

- Gate uses `test_gate_remote_unlock.py`, with RC522 IRQ on GPIO21.
- House uses `test_house_remote_unlock.py`; GPIO14 opens the gate and
  GPIO18 answers/ends a call. Gate GPIO14 calls the house without unlocking.
- Both speakers chime after call acceptance. RINGING/TALKING/IDLE control
  transitions and remote opening were exercised on hardware. TALKING still
  sends no microphone audio.
- RFID opens locally. RC522 intermittently loses configuration; automatic
  restoration is an active workaround, not a resolved fault.
- The capacitor test did not eliminate the fault. The last reported run
  showed 8 reset attempts, 8 restorations and 0 recovery failures. The
  installed capacitor value was not explicitly confirmed in that report.
- Both nodes in that run selected the repeater (`SOURCE = "ap"`). Previous
  router-to-repeater tests also worked.
- Keep USB power and manual Thonny startup. No deployment or automatic
  application startup is part of this checkpoint.

Open problems and limits:

- During recovery RFID exchanges pause; the 15-second retry cooldown can
  leave access by tag unavailable for several seconds. Remote call/open
  controls continue being serviced.
- Lost RC522 settings, startup timeouts and the all-zero SPI read incident
  are recorded below; the underlying electrical/software cause is unknown.
- A held tag can repeatedly extend the unlock interval.
- Nonblocking RFID removed the previously reported chime interruption in
  one test, but uninterrupted playback during recovery is not guaranteed.
- One log ended a call with `House unreachable`; whether the house board
  was deliberately stopped is unconfirmed.
- Earlier UDP duplex audio hit `ENOMEM`; its cause and long-term audio
  stability remain unresolved.

Next stage: enable two-way microphone audio only while TALKING, sharing
speaker ownership with the chime. Answer starts audio; hangup, opening,
timeout or peer loss must stop it. Keep this checkpoint on the current
branch before implementing audio. PR creation is deferred until requested.

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

## 2026-10-22 - two-board audio retest confirmed

The restored two-board audio setup works, as reported after the retest.
The connected access points and repeater behavior are not yet identified.
Startup diagnostics now list visible BSSIDs for the configured SSID and
print the connected SSID, IP, and RSSI once. Connected BSSID is printed
only if supported by the firmware; scan results alone do not identify the
connected access point. The continuous received-audio meter was removed.
Startup diagnostics were exercised on hardware; explicit BSSID selection
was subsequently reported working in the router/repeater audio test.

## Audio setup and network test checklist

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
pins the connection to the configured BSSID as described below. It does
not implement application-level reconnection handling or automatic
switching between access points. Recovery remains unverified.

## Following stages

1. Add a network command from the house board to unlock the gate, retaining
   local RFID and button control.
2. Integrate audio and unlocking, then add gate-side calling and the
   house-side chime.
3. Prepare standalone ESP32 power and recoverable automatic startup.

HC-SR501 motion sensing is deferred and does not block these stages.

### Explicit access point selection

`secrets.py` now requires `SOURCE = "router"` or `SOURCE = "ap"` for the
UDP duplex script. Router BSSID: `D4:B7:09:CA:45:36`; repeater (`ap`)
BSSID: `08:8A:F1:D9:D4:5E`. The script resets Wi-Fi at startup and pins
its connection to the selected BSSID, with a 20-second connection timeout
and no fallback. Startup output identifies the enforced BSSID and RSSI.
Test one board on each source with distinct static IPs and reciprocal
peer IPs. On 2026-10-22, audio with one board selecting the router and
the other selecting the repeater was reported working. Long-duration
stability and recovery after connection loss remain unverified.

The first diagnostic run reported `ENOMEM` during audio streaming. Its
cause remains unresolved; successful Wi-Fi connection alone does not
confirm stable audio.

## 2026-10-22 - IRQ gate controller preserved

`firmware/gate-node/test_gate_unlock_irq.py` preserves the executable logic
of the working script supplied from Thonny. It uses the same gate pinout
as the polling controller, plus RC522 IRQ connected to GPIO21 with an
internal pull-up. Both the button and RFID use falling-edge interrupts;
RFID also retries REQA every 200 ms. The whitelist and 3-second unlock
setting are unchanged.

The IRQ variant was reported working, while the polling variant did not
work in the latest attempt. The earlier successful polling checkpoint
remains recorded above. The cause of this difference is not established;
compare both variants after a full board reset before selecting one for
network integration. Successful access does not establish that IRQ fires
only for tag responses; earlier diagnostics observed spurious IRQ events.
The original `test_gate_unlock.py` remains unchanged. No automatic startup
or network commands have been added to either controller.

## Remote unlock implementation - hardware test pending

Added `test_gate_remote_unlock.py` based on the preserved IRQ gate
controller, `test_house_remote_unlock.py`, and shared `lib/remote_link.py`.
Control uses UDP 5007, explicit BSSID selection, acknowledgement/retry,
and a bounded duplicate-request cache. Gate Wi-Fi retries do not wait in
the local RFID/button loop. Audio and automatic startup remain separate.
See `remote-unlock.md` for uploads, wiring, behavior, and the test checklist.
Hardware confirmation is pending; the existing gate and audio checkpoint
scripts remain unchanged.

## 2026-10-22 - remote unlocking confirmed

Hardware test confirmed opening from both buttons and RFID in the initial
remote-unlock version. Gate: `192.168.1.237`, router BSSID
`D4:B7:09:CA:45:36`, RSSI -63 dBm. House: `192.168.1.238`, repeater BSSID
`08:8A:F1:D9:D4:5E`, RSSI -53 dBm. Three remote request IDs had matching
house confirmations and gate unlock logs. Loss/recovery tests and extended
stability are not yet confirmed.

## Gate calling and house chime - hardware test pending

The current remote scripts now give the gate button its intended calling
role: it sends `CALL` and no longer unlocks locally. RFID and the house
button still unlock. House `chime.py` plays two short tones through the
existing MAX98357A speaker wiring (BCLK7/LRC8/DIN9); the microphone stays
unused. Upload `chime.py` alongside the house script. Calls use retries,
acknowledgements, a 10-second duplicate cache, and a one-second gate-side
cooldown. Offline calls are not queued. This change does not alter the
preserved standalone gate test scripts.

## 2026-10-22 - gate-to-house chime confirmed

The gate button successfully rang the house speaker using the remote
scripts. This is the hardware checkpoint before adding call states.

## Call controls - hardware verification pending

Added shared `lib/intercom_session.py`: gate calls ring both speakers once
the house accepts the request. The house owns call state and sends it every
500 ms with a session ID and increasing revision. Gate button presses are
ignored while a call is active. Repeated/stale packets do not replay the
chime or revert a newer state. The house talk button is GPIO18 to GND:
RINGING -> TALKING -> IDLE. The house open button remains GPIO14 and ends
an active call when sending an unlock request. RFID still opens locally.

This is a control-only test: TALKING does not transmit microphone audio.
Unanswered calls expire after 30 seconds, TALKING after 120 seconds; missing
peer heartbeats end the call after approximately 3 seconds. No call is
restored automatically after a restart. Duplicate history is bounded and
volatile. Host-side session checks cover retries, answer/hangup, stale state
and loss of peer contact; physical verification remains pending.

## RFID regression during call-control test - fix pending hardware verification

RFID was reported to unlock once and then stop working reliably. Corrected
IRQ polarity and rearm ordering in the shared MFRC522 driver and added a
missed-response check plus five-second IRQ/read counters to the remote gate
script. Host-side checks cover register-write ordering and RxIRq handling;
repeat hardware scans are still required. See `rfid.md` for details.

### RFID/chime follow-up

Updated-driver test still stalled at 55 successful reads while calls and
remote unlock continued. Gate chime interruptions were reported. Replaced
blocking UID reads in the remote gate loop with a two-stage asynchronous
exchange, gated by RxIRq with 40 ms response deadlines and 200 ms scan
cycles. Added RFID stage/max service duration diagnostics. Simulated checks
cover false IRQ, successful UID response, timeout and subsequent scan;
repeat hardware testing remains pending. The complete hardware failure
cause is not yet established.

### Manual RC522 recovery tools - hardware test pending

Added `lib/rfid_debug.py` and console wrappers `rfid_status()`,
`rfid_probe(10)`, `rfid_reset()`, and `rfid_reset(hardware=True)`.
These compare reads after interruption, software reset, and an RC522-only
RST pulse without cycling ESP32 power. Probes never operate the relay.
Driver reset now waits for oscillator startup with a bounded readiness
check. Host-side checks cover snapshot/reset separation, both reset modes,
probe bounds and reset timeout. Results on the failing hardware are pending.

### 2026-10-22 - reader configuration loss and software recovery confirmed

After reads stopped at 8, the manual snapshot showed Version=0x82,
TxControl=0x80 (antenna driver enable bits clear), TMode=0x00,
TPrescaler=0x00 and TReload=0x0000. SPI register reads still worked.
A ten-second probe before reset found zero UIDs. Manual software reset and
initialization restored TxControl=0x83, TMode=0x8D, TPrescaler=0x3E,
TReload=0x001E; the following ten-second probe read the tag ten times.
This confirms loss of operating configuration and recovery by software
reinitialization, not the underlying cause. Possible supply disturbance,
reset-line disturbance or unintended register writes remain unverified.
The failure followed gate chime activity in this run. Next isolate gate
amplifier load with a powered-down wiring change and repeat the same test,
retaining the software and checking register snapshots after any failure.
No automatic reset/recovery has been added.

### RC522 configuration-loss recovery

Manual hardware test: failing state had antenna bits disabled and timer
registers zeroed; baseline probe read zero tags. Software reset restored
the expected settings and the subsequent probe read the tag 10 times.
Added `lib/rfid_recovery.py` to detect lost stable configuration once per
second and restore it with a staged software reset, post-reset verification,
and a 15-second minimum between attempts. Gate diagnostics include reset,
restore and failure counters. Host-side tests cover healthy operation,
configuration loss, reset readiness/timeout, cooldown and subsequent retry.
Automatic recovery on hardware remains to be confirmed; the underlying
cause of configuration loss remains unknown.

### RC522 startup reset timeout

A hardware attempt stopped in the driver's startup reset readiness check,
before automatic recovery could start. Added explicit 10 ms RST-low and
50 ms startup settling delays, one bounded startup retry using the RST pin,
and Command/Version register values in timeout errors. This startup-only
retry may block initialization; runtime recovery remains staged. Hardware
verification is pending; persistent failure is not suppressed.

### Load-isolation test prepared

Added `test_rfid_isolation.py` with separate RFID-only, chime, and relay
modes, holding Wi-Fi configuration constant. Tags never actuate the relay;
GPIO14 applies only the selected load. Lost stable RC522 configuration
prints a snapshot and stops without automatic recovery. Hardware outcomes
are pending; see `rfid.md` for the staged comparison procedure.

### RFID isolation baseline and return to polling

After a full USB power cycle, RFID-only isolation with Wi-Fi enabled ran
for approximately 80 seconds and recorded 36 reads across multiple tags,
without detected configuration loss. The earlier all-zero register snapshot
occurred before this power cycle. No chime/relay isolation result is yet
confirmed; voltage disturbance remains a hypothesis.

Further IRQ diagnosis is deferred. The integrated gate script now uses
SPI polling without configuring GPIO21 or routing reader interrupts to its
IRQ pin. REQA and anticollision still advance across loop iterations to
avoid reintroducing audio stalls. Automatic configuration recovery and its
counters remain enabled, so reset counts must be checked before declaring
polling stable. The shared driver keeps opt-in IRQ wrappers for preserved
standalone tests. Disconnect RC522 IRQ with power removed; the remaining
pinout, house script and call controls are unchanged. Hardware verification
of this integrated polling variant is pending.

### Integrated polling trial rejected; IRQ restored

The integrated polling trial did not detect tags in the reported hardware
attempt. Restored the exact pre-trial driver/controller implementation:
GPIO21 falling-edge RFID notification, nonblocking REQA/UID steps, manual
diagnostics, startup reset delays/retry, and automatic configuration
recovery with counters. Reconnect RC522 IRQ to GPIO21 with power removed.
Call controls and house code are unchanged. Restoration does not establish
long-term stability or resolve the cause of configuration loss.


## Integrated voice implementation - hardware test pending

Added `lib/intercom_audio.py` and shared speaker ownership with the chime.
The existing house/gate scripts service nonblocking microphone capture,
UDP send/receive and speaker playback only in TALKING. Ending a call stops
voice and restores chime ownership; no microphone is initialized in IDLE
or RINGING. Audio datagrams carry the call ID and sequence number. Bounded
playback buffers and receive work avoid unbounded queue growth; transient
send errors including ENOMEM are counted instead of stopping gate control.

Four host-side tests passed for state-gated resource lifecycle, session/
peer/sequence filtering, send failure handling, and initialization cleanup.
Hardware timing, acoustic feedback, repeated-call stability and coexistence
with RFID recovery remain to be verified. Standalone audio checkpoint is
unchanged. No PR or deployment is part of this stage.

### Repeated ding-dong during incoming calls - hardware test pending

Both nodes now repeat a high-then-low 880/660 Hz chime while RINGING,
with a pause between pairs and a 30-second local limit. Answer/open/end
stops and releases the speaker, discarding queued chime samples before
voice takes ownership. Six host-side tests pass, including repetition,
timeout, immediate stop/reopen and existing voice lifecycle/transport checks.

### Integrated audio failure report - diagnosis pending

Voice was reported absent even before the repeated-chime change. House
reported sent packets and zero accepted receives; no gate audio counters
were reported. The submitted peer IPs and ports are reciprocal and match.
The cause is not yet established. Added role/version startup identification,
state/Wi-Fi/running status even when audio is inactive, microphone completion
and raw/rejected datagram counters. Both updated scripts and shared modules
must be uploaded together. Working standalone audio uses immediate blocking
I2S duplex without session headers; integrated audio uses TALKING gating,
callbacks and call/sequence filtering. No Wi-Fi credentials were recorded.
