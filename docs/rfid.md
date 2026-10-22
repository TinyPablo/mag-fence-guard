# RFID

Reader: MFRC522 (RC522 breakout, SPI-only - see `CONTEXT.md`). 6 physical
tags/keyfobs (13.56MHz).

## Confirmed working

`firmware/gate-node/test_rfid.py` reads and prints UIDs correctly on the
ESP32 (MicroPython). Tested 2026-07-16 against all 6 tags plus a phone's
NFC (out of curiosity - not part of the actual whitelist).

One transient garbled-byte glitch was seen once during testing (junk bytes
printed to the REPL mid-read) - not reproduced since, not investigated
further yet.

## Known tag UIDs

```
E9-55-91-29
67-2F-3A-CC
3C-EE-5A-4A
6C-0F-2A-49
17-D5-0E-CC
DC-FA-14-4A
```

## LED + whitelist test

`firmware/gate-node/test_led_presence.py` lights the onboard ESP32 LED
(GPIO2) only for the 6 known UIDs above, and prints every detected UID plus
whether it matched. Confirmed working. Detection is plain SPI polling
(`request()`/`anticoll()` every ~150ms) - see "IRQ pin: tried and dropped"
below for why this isn't interrupt-driven.

The RC522 breakout's own onboard LED (silkscreened "D1") is a fixed
power-on indicator wired straight to 3.3V - it isn't GPIO-controllable and
isn't related to this test.

## IRQ pin: tried and dropped

Wired RC522 IRQ to ESP32 GPIO4 and added `enable_irq_on_detect()` to
`lib/mfrc522.py` (`ComIEnReg = 0xA0`, routing `RxIRq` to the physical IRQ
pin) to see if the pin could signal tag presence instead of polling.

Two things came out of this experiment:

- **A scary but unrelated false alarm:** right after wiring IRQ, RFID
  appeared to stop responding entirely (even plain UID reads). This turned
  out to be a MicroPython/ESP32 gotcha, not a wiring or code problem:
  Thonny's "Run" only soft-reboots the interpreter (like Ctrl+D), which
  doesn't reset the ESP32's own hardware peripherals (SPI unit, GPIO mux
  state). Leftover state from a previous script can persist across a soft
  reboot and break the next run. A full power cycle (or the board's
  physical EN/RST button) fixes it. Unrelated to the RC522's own RST pin,
  which the driver already toggles correctly every run - worth remembering
  for future firmware work on this board in general, not just RFID.
- **The IRQ pin itself wasn't a useful signal even once communication was
  restored:** it read as "fired" on nearly every poll cycle, tag present or
  not. Cause: `_tocard()` (used internally by `request()`/`anticoll()`)
  enables a broad interrupt mask (`0x77` - several sources including
  `TimerIEn`) on every transceive, overriding the narrower `RxIEn`-only
  mask meant to isolate tag detection. A timeout with no tag present still
  fires *some* enabled interrupt, so the pin can't cleanly distinguish
  "tag present" without deeper driver surgery.

**Decision:** dropped. For this project, gate access is human-paced (a tag
held near the reader for roughly a second), so ~150ms polling latency is
imperceptible - there's no real benefit to interrupt-driven RFID detection
here, and the added complexity isn't worth it. `enable_irq_on_detect()` was
removed from `lib/mfrc522.py`, IRQ is left unconnected. Physical buttons
(planned separately) are a different story - GPIO interrupts
(`machine.Pin.irq()`) are the standard, well-trodden approach there and
don't have this complication.

## IRQ pin: tried again with a narrower mask, still dropped

Retried on the ESP32-S3 (N16R8) board, this time going after the actual
root cause instead of the pin behavior: `_tocard()` always resets
`ComIEnReg` to a broad `0x77` mask (includes `TimerIEn`), which is what
made the pin fire on nearly every cycle the first time. Added
`arm_irq()`/`disarm_irq()` to `lib/mfrc522.py`, bypassing `request()`
entirely to send REQA with a narrow `ComIEnReg = 0x20` (`RxIEn` only, no
`TimerIEn`) mask, with a host-side retry timer (resend REQA every 200ms)
standing in for the RC522's own timeout interrupt.

Result, measured with a diagnostic build that logs `ComIrqReg` at every
pin trigger: the physical IRQ pin still fired almost immediately after
every REQA send (~13ms), tag present or not. `ComIrqReg` read `0x44`
(`TxIRq` + `LoAlertIRq`) every time, with `RxIRq` (the bit we actually
enabled) never set. So the pin is triggering on the RC522's own
transmission completing, not on a tag response - even though those
sources (`TxIEn`, `LoAlertIEn`) were explicitly left disabled in
`ComIEnReg`. That's not a masking bug on the host side; it points to this
being a cheap RC522 clone that doesn't fully honor `ComIEnReg` masking on
the physical pin.

**Decision:** dropped again, same reasoning as before (human-paced access,
150ms polling is imperceptible) but now with harder evidence it's a
hardware limitation, not a fixable masking bug. `arm_irq()`/`disarm_irq()`
are left in `lib/mfrc522.py` (harmless, unused by the polling scripts) in
case a genuine NXP-chip reader is tried later. `test_gate_unlock.py` uses
plain polling for RFID; only the button is interrupt-driven there.

## Open

Whitelist management approach (hardcoded vs. an enrollment mode) is not
decided yet - see `CONTEXT.md`.

## IRQ rearm correction during intercom integration

A later hardware attempt read one tag and then stopped responding reliably.
Inspection found `arm_irq()` wrote `ComIEnReg = 0x20` despite the GPIO
handler expecting an active-low falling edge. The revised sequence uses
`0xA0` (IRqInv + RxIEn), stops the previous command before clearing IRQ
flags/flushing FIFO, and disables IRQ routing while disarming. The gate
remote script also checks RxIRq at the retry deadline to recover a missed
GPIO edge, and prints diagnostic counters every five seconds.

These changes follow the register definitions in the
[NXP MFRC522 data sheet](https://www.nxp.com/docs/en/data-sheet/MFRC522.pdf).
The earlier clone-hardware explanation is not conclusive given the
configuration defect. The cause of the current intermittent failure and
hardware effectiveness of this correction remain unverified. No automatic
reader resets or changes to access policy were added. The shared driver
change also affects the preserved IRQ test scripts when this driver is
uploaded with them; their controller source files remain unchanged.

## Nonblocking RFID exchange in the remote gate controller

After the polarity correction, hardware logs still showed the UID read
counter stuck at 55 while call control and remote unlock continued.
Interrupted gate-side chime playback was also reported. The previous gate
loop called blocking `anticoll()` for every GPIO IRQ, even without RxIRq.
This could stall the shared loop on unsuccessful exchanges; the logs do
not establish the complete cause of the lost reader response.

The remote gate controller now runs REQA and UID anticollision as separate
steps across loop iterations. Only RxIRq advances an exchange; a GPIO IRQ
is a diagnostic hint. Each response has a 40 ms deadline, and a new cycle
starts no faster than every 200 ms. `start_anticoll_irq()` and
`finish_anticoll_irq()` avoid the synchronous driver's 2000-iteration wait.
RFID is armed after network/chime initialization. Diagnostics include the
current stage and maximum RFID service duration since the previous report.
The original synchronous methods remain available for standalone tests.
Hardware verification of repeated removal/re-presentation and chime quality
is pending. Holding a recognized tag can still extend the unlock timer.

## Manual reader diagnosis from the gate console

Upload `lib/rfid_debug.py`, updated `lib/mfrc522.py`, and
`test_gate_remote_unlock.py` to the gate. After reproducing the loss of
reads, interrupt with Ctrl+C in the Thonny Shell. Do not soft-reboot or
rerun the script before collecting the snapshot: interpreter restart loses
the reader object, and rerunning initializes the chip. The gate script's
cleanup closes networking/audio, detaches handlers and de-energizes the
relay. The following probes do not unlock or run the intercom.

At the retained `>>>` prompt, run these commands individually:

```python
rfid_status()
rfid_probe(10)
rfid_reset()
rfid_probe(10)
```

Present/remove a tag during each ten-second probe. `rfid_status()` reads
registers without resetting the chip; a probe restarts radio exchanges but
does not reinitialize the chip. Compare this baseline with the result after
`rfid_reset()`, which issues a software reset and restores configuration.
If that does not restore reads, separately try:

```python
rfid_reset(hardware=True)
rfid_probe(10)
```

The latter pulses RC522 RST (GPIO16), then initializes the reader; it does
not cycle its power or restart ESP32. Preserve all outputs and restart the
gate application only after the comparison. Reset now waits for oscillator
startup and checks PowerDown with a bounded timeout before configuration
writes. Resets occur only at normal initialization or explicit manual
request; no automatic recovery was added. A register snapshot is not by
itself proof of the hardware fault's cause.

## Configuration-loss recovery in the remote gate script

Hardware comparison showed `TxControl=0x80` (antenna driver bits off) and
zeroed timer configuration after the failure. Manual software reset and
reinitialization restored `TxControl=0x83`, timer settings, and 10 successful
reads after a zero-read baseline probe. This establishes successful recovery
in that test, not the cause of configuration loss.

`lib/rfid_recovery.py` now checks stable antenna, timer, TxASK and Mode
configuration once per second. It does not infer failure from absent tags.
A mismatch pauses RFID exchanges, issues a software reset, waits across
loop iterations for at least 50 ms, and checks reset readiness for up to
150 ms. It then calls `init(reset=False)` and verifies configuration before
the gate restarts REQA. Calls, network service, chime and relay timing
continue during the reset wait. SPI configuration writes themselves still
take time; recovery is not a guarantee of uninterrupted playback.

Reset attempts are separated by at least 15 seconds. Failures leave RFID
exchanges paused until the next attempt; local network controls continue.
Counters distinguish attempts, restored configurations and failed resets.
No chip power cycling or automatic ESP32 restart is performed. Upload the
new module, updated driver and updated gate script together. Automated
recovery still needs hardware verification and does not replace diagnosis
of repeated configuration loss, including possible power or wiring issues.

## Isolating load-related configuration loss

`test_rfid_isolation.py` runs one manually selected `MODE`: `rfid`,
`chime`, or `relay`. Tags only print UIDs and never unlock in this script.
GPIO14 triggers the selected load: no action in `rfid`, gate speaker chime
in `chime`, or a three-second relay activation in `relay`. Network unlock
commands are ignored. Wi-Fi defaults to enabled through the existing
`RemoteLink` and per-board secrets so its load stays present across all
three comparisons. It can be disabled for a separate baseline comparison.

Upload the test and the existing `lib/mfrc522.py`, `lib/rfid_debug.py`,
`lib/rfid_recovery.py`, `lib/remote_link.py`, `/chime.py`, and `/secrets.py`.
Run only this script on the gate. Keep physical wiring unchanged and restart
between modes. The house may remain powered but cannot control this test.
No microphone or intercom session runs. In baseline mode the amplifier
remains physically powered if connected, but I2S playback is not initialized.

For each mode, test for two to three minutes with repeated tag removal and
presentation. Start with `MODE = "rfid"`. Only if stable proceed to `chime`
and press the gate button between/during tag scans; then test `relay` with
both relay transitions and tag scans. Relay mode physically releases the
magnet. Record which load/transition preceded any failure. Configuration
is inspected once per second. A mismatch prints a snapshot, stops the test,
and returns the relay to its de-energized state without resetting RC522.
Only the condition-check helper is used; automatic recovery is disabled.
If reads stop without configuration loss, Ctrl+C and `rfid_debug.status(reader)`
preserve a register snapshot. Startup reader reset/retry still applies.

## Current integrated mode: polling without physical IRQ

The integrated `test_gate_remote_unlock.py` now uses `start_request()`,
`response_ready()`, `start_anticoll()` and `finish_anticoll()` to poll SPI
response flags. Reader IRQ routing is disabled and GPIO21 is unused.
Disconnect the IRQ wire with power removed. The scan cycle remains 200 ms
with 40 ms response deadlines; there is no tight synchronous wait loop.
This preserves the nonblocking behavior required by chime playback.

Automatic configuration recovery remains enabled and reported in the
counters. Polling alone is not established as a cure for configuration loss.
The preserved standalone IRQ scripts opt in through their original wrappers.

## Current selection after polling trial: IRQ restored

The integrated polling trial above was reported not to detect tags and
was reverted. Current `test_gate_remote_unlock.py` again uses RC522 IRQ on
GPIO21, nonblocking exchanges and configuration recovery. The driver polling
wrappers introduced for that trial were removed. The earlier standalone
polling checkpoints and isolation test remain available; this does not
establish a general failure of polling. Startup prints `RFID IRQ GPIO21`.


## Capacitor/recovery hardware result

After the capacitor experiment, configuration loss continued. The reported
integrated IRQ run recorded 8 automatic reset attempts, 8 successful
restorations and zero recovery failures. Installed capacitance was not
explicitly confirmed in the result. Recovery is now hardware-confirmed for
that run, while power integrity and the cause of register loss remain
unresolved. The reset cooldown introduces temporary tag-access outages;
this checkpoint must not be described as stable uninterrupted RFID access.
