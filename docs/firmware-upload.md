# Command-line firmware upload

Use the Mac terminal, not the MicroPython REPL or Thonny `%run` command.
The local `tools/firmware.py` uses mpremote and is never uploaded to ESP32.

## Setup

```sh
python3 -m venv /private/tmp/mag-fence-tools
/private/tmp/mag-fence-tools/bin/python -m pip install mpremote
/private/tmp/mag-fence-tools/bin/python tools/firmware.py ports
```

Close Thonny serial connections first. If a port is busy, inspect its owner
with `lsof /dev/cu.usbmodem101 /dev/cu.usbmodem1101`; do not terminate unknown
processes. USB paths can change. `--port id:<serial>` also accepts the USB
serial printed by `ports`.

## Upload

Run from the repository root, substituting each board's actual port:

```sh
/private/tmp/mag-fence-tools/bin/python tools/firmware.py upload gate --port /dev/cu.usbmodem101 --source auto
/private/tmp/mag-fence-tools/bin/python tools/firmware.py upload house --port /dev/cu.usbmodem1101 --source auto
```

Role preflight checks the existing STATIC_IP: gate `.237`, house `.238`.
A wrong role/port combination stops before copying files. Existing secrets.py
must already be configured. Without `--source` it is preserved unchanged;
with that flag only SOURCE assignments are updated, leaving credentials and
addresses intact. secrets.py, boot.py and main.py are never part of the
upload manifest. Application files are overwritten in place, not as an
atomic whole-device deployment; rerun after any interrupted copy.

The uploader checks generated snippets locally, copies all role files,
verifies SHA256 hashes on the board and checks loaded module versions.
It does not enable automatic boot. Firmware 0.5.0 includes tag_presence.py
on the gate and unlock_notice.py on both nodes.

## Run and monitor

After a successful upload, either open Thonny and run the role script, or
append `--run` to upload to immediately start and monitor the program.
Use two terminal windows for two running boards. Keep Thonny closed while
mpremote owns a port. Ctrl+C interrupts the monitor; reconnect to confirm or
stop the board program. Opening Thonny may interrupt/restart the interpreter.
Use a physical USB power cycle when the established RFID startup issue
requires it; soft-reset is not equivalent to a power cycle.

A preview without connecting is available with `--dry-run`. The corrected
SOURCE code generation is covered by host-side tests. Actual hardware
upload verification is still pending after the earlier SyntaxError report.
