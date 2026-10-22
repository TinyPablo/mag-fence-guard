# HC-SR501 standalone bring-up

Gate ESP32-S3 wiring: PIR OUT to GPIO13, VCC to 5V, GND to GND. Jumper H
selects retriggering: further detected movement can extend the HIGH output.
The module's output is nominally 3.3V logic even with 5V supply. Follow the
labels on the actual module rather than assuming pin orientation.

Reference: [HC-SR501 supplier guide](https://shillehtek.com/blogs/shillehtek-product-manuals/hc-sr501-pir-motion-sensor).
Allow approximately 30-60 seconds after applying power for stabilization.
The standalone script deliberately labels its first 60 seconds WARMUP,
even if the sensor was already powered. Startup pulses are not a confirmed
fault. HIGH is a sensor output with an adjustable hold time, not proof that
a person is continuously present; LOW is not proof of an empty area.

## Test procedure

1. Stop the integrated gate program. Open the LOCAL
   `firmware/gate-node/test_pir_motion.py` in Thonny and press F5.
   This runs only the PIR test, without changing application startup files.
2. Keep clear of the sensor during the 60-second WARMUP period. Adjust the
   potentiometer marked TIME to a short delay, and sensitivity to a moderate
   setting. Identify the pots by the actual board markings; do not assume
   left/right placement or force the end stops.
3. After READY, move across the sensor's view; look for OUT=1 HIGH.
4. Leave its view and remain still; wait for OUT=0 LOW. Its log reports the
   measured duration of HIGH. In H mode continued movement extends HIGH.
5. Repeat at several distances, then leave it undisturbed for a few minutes.
   Collect the transitions/status output if HIGH never clears or LOW never
   rises. A status line every 10 seconds confirms the test is still running.

A short period after LOW during which retriggering is suppressed may be
normal for the module. Actual hold/block intervals vary across boards.
No PIR-to-house events, chime, unlock or voice behavior is integrated yet.

The role uploader/bundle now includes `/test_pir_motion.py` on the gate.
After running the generated gate updater and resetting, the Shell can start
it using `exec(open('/test_pir_motion.py').read())`. The PIR test identifier
is `pir-test-0.1.0`; the integrated application remains firmware 0.5.0.

## Integrated automatic exit - firmware 0.6.0

GPIO13 now requests a 15-second local unlock on a qualified LOW-to-HIGH
transition. The common unlock path ends calls/voice, plays the gate buzz
for the unlock interval and sends a short house notice with source `pir`.
Movement during an existing unlock is ignored and does not extend it. After
relocking the input must be LOW for at least 200 ms before a new rising
edge can trigger. Other valid access sources do not shorten an already
longer unlock interval. This is automatic exit for any detected movement
in the inside-facing field of view; it does not identify people/direction.

The default warm-up is 60000 ms after application initialization, handled
without sleeps in the control loop. Only PIR is suppressed; other features
remain available. The input must return LOW after warm-up before arming,
even if it was already HIGH at startup. Keep the hardware hold time near
1-2 seconds and jumper H.

For supervised tests ONLY when the PIR has already been powered/stabilized,
start from a fresh Shell prompt without power cycling the sensor:

```python
import secrets
secrets.PIR_WARMUP_MS = 0
exec(open('/test_gate_remote_unlock.py').read())
```

This override changes only the current interpreter's module object, not
secrets.py on disk. A soft/hard reboot discards it. Do not skip warm-up
immediately after powering the PIR. An optional permanent PIR_WARMUP_MS in
secrets.py overrides the default, but 60000 is recommended for normal use.

Upload the full 0.6.0 gate/house release; regenerated Thonny update files
include new gate `/lib/pir_exit.py` and support house notifications from PIR.
Check: other controls work during warm-up; startup HIGH cannot open; motion
after LOW opens for 15 seconds; repeated motion cannot extend; a new LOW/HIGH
cycle after relocking can open again; house receives one brief notification.
Test actual sensor placement before relying on automatic exit.
