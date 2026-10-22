#!/usr/bin/env python3
"""Upload a complete role-specific MicroPython application using mpremote."""

import argparse
import ast
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'firmware/gate-node/lib'
ROLE_IP = {'gate': '192.168.1.237', 'house': '192.168.1.238'}
SHARED = ('firmware_info.py', 'remote_link.py', 'intercom_session.py', 'intercom_audio.py', 'unlock_notice.py')
GATE = ('mfrc522.py', 'rfid_debug.py', 'rfid_recovery.py', 'tag_presence.py')


def files_for(role):
    files = {'lib/' + name: LIB / name for name in SHARED}
    if role == 'gate':
        files.update({'lib/' + name: LIB / name for name in GATE})
    files['chime.py'] = ROOT / 'firmware/house-node/chime.py'
    script = 'test_' + role + '_remote_unlock.py'
    files[script] = ROOT / ('firmware/' + role + '-node') / script
    return files


def mpremote(args):
    return [sys.executable, '-m', 'mpremote'] + args


def execute(args):
    subprocess.run(mpremote(args), check=True)


def preflight(role, source):
    # Only non-secret fields are printed. Wrong-board uploads stop before copies.
    code = (
        "import os, machine\n"
        "try:\n import secrets\n"
        "except ImportError:\n raise RuntimeError('Missing /secrets.py; configure this board first')\n"
        "actual = getattr(secrets, 'STATIC_IP', None)\n"
        "print('Board IP:', actual, 'peer:', getattr(secrets, 'PEER_IP', None))\n"
        f"if actual != {ROLE_IP[role]!r}: raise RuntimeError('Wrong board for selected role; check USB port and STATIC_IP')\n"
        "try:\n os.mkdir('/lib')\n"
        "except OSError:\n"
        " if not os.stat('/lib')[0] & 0x4000: raise\n"
    )
    if source is not None:
        code += (
            "path = '/secrets.py'\n"
            "with open(path) as f: original = f.read()\n"
            "lines = [line for line in original.splitlines() if line.split('=', 1)[0].strip() != 'SOURCE']\n"
            f"lines.append({('SOURCE = ' + repr(source))!r})\n"
            "updated = '\\n'.join(lines) + '\\n'\n"
            "with open(path, 'w') as f: f.write(updated)\n"
            f"print('WiFi SOURCE updated to', {source!r})\n"
        )
    return code


def verify_code(files, role):
    hashes = {target: hashlib.sha256(path.read_bytes()).hexdigest()
              for target, path in files.items()}
    return (
        "import hashlib, binascii\n"
        f"expected = {hashes!r}\n"
        "for name, checksum in expected.items():\n"
        " h = hashlib.sha256()\n"
        " with open('/' + name, 'rb') as f:\n"
        "  while True:\n"
        "   chunk = f.read(1024)\n"
        "   if not chunk: break\n"
        "   h.update(chunk)\n"
        " if binascii.hexlify(h.digest()).decode() != checksum:\n"
        "  raise RuntimeError('Upload checksum mismatch: ' + name)\n"
        " print('Verified:', name)\n"
        "import lib.remote_link, lib.intercom_session, lib.intercom_audio, lib.unlock_notice, chime\n"
        + ("import lib.mfrc522, lib.rfid_debug, lib.rfid_recovery, lib.tag_presence\n" if role == 'gate' else '')
        + "from lib.firmware_info import VERSION, report\n"
        + f"report({role!r}, VERSION)\n"
    )


def upload_commands(role, port, source=None, run=False):
    files = files_for(role)
    for path in files.values():
        ast.parse(path.read_text(), filename=str(path))
    setup = preflight(role, source)
    verification = verify_code(files, role)
    compile(setup, '<device-preflight>', 'exec')
    compile(verification, '<device-verification>', 'exec')
    commands = ['connect', port, 'soft-reset', 'exec', setup]
    for target, path in files.items():
        commands += ['fs', 'cp', str(path), ':/' + target, '+']
    commands += ['soft-reset', 'exec', verification]
    if run:
        # Run the exact local script just verified on the board; monitor output.
        commands += ['run', str(files['test_' + role + '_remote_unlock.py'])]
    return commands


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    subs.add_parser('ports', help='List USB serial ports via mpremote')
    upload = subs.add_parser('upload', help='Copy and verify every file for a role')
    upload.add_argument('role', choices=ROLE_IP)
    upload.add_argument('--port', required=True, help='USB path or id:serial from ports')
    upload.add_argument('--source', choices=('auto', 'router', 'ap'),
                        help='Explicitly update only SOURCE in board secrets.py')
    upload.add_argument('--run', action='store_true', help='Start application and follow logs')
    upload.add_argument('--dry-run', action='store_true', help='Print file mapping without connecting')
    args = parser.parse_args(argv)
    if args.action == 'upload' and args.dry_run:
        for target, path in files_for(args.role).items():
            print(str(path.relative_to(ROOT)) + ' -> /' + target)
        print('secrets.py: preserved' if args.source is None else 'secrets.py: only SOURCE updated')
        return 0
    try:
        if args.action == 'ports':
            execute(['connect', 'list'])
        else:
            print('Close Thonny serial connections before uploading.', flush=True)
            print('Uploading role:', args.role, 'port:', args.port, flush=True)
            execute(upload_commands(args.role, args.port, args.source, args.run))
            if not args.run:
                print('Upload verified. Start manually in Thonny or repeat with --run.')
        return 0
    except subprocess.CalledProcessError as error:
        print('mpremote failed; see the device error above. No further upload steps were run.', file=sys.stderr)
        return error.returncode or 1
    except KeyboardInterrupt:
        print('\nMonitor interrupted; reconnect to the board to check/stop its application.')
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
