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

## Update directly through two Thonny windows

Run `python3 tools/firmware.py bundle` on the Mac after firmware changes.
It generates ignored local artifacts `updates/update_gate.py` and
`updates/update_house.py`, containing role-specific application files and
SHA256 checksums. No mpremote dependency or USB port is needed to build.

In the Thonny window for each board, choose Open > This computer, open the
matching generated updater and press F5. The updater executes on the board,
checks STATIC_IP before writes, leaves secrets.py/boot.py/main.py untouched,
skips identical files and verifies changed files before renaming their
per-file temporary replacements. It never clears the whole filesystem.
A failed/interrupted multi-file update may leave mixed application versions;
rerun the updater to complete it. Existing version checks detect mixing.
Generated payloads contain no credentials and may use more interpreter
memory than individual file transfers; actual board execution is pending.

After SUCCESS, close old application editor tabs. Power-cycle each board,
then use its Shell (not a Mac terminal) to start the installed application:

```python
exec(open('/test_gate_remote_unlock.py').read())
```

Use `/test_house_remote_unlock.py` in the house window. Settings including
SOURCE are preserved; use `SOURCE = "auto"` in secrets.py for automatic AP
selection. New application files require updating the single role manifest
in tools/firmware.py, then rebuilding both updater artifacts. Neither an
automatic boot script nor an automatic board restart is installed.
