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
