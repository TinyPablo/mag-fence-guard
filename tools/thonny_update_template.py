# Generated firmware updater: open this LOCAL file in Thonny and press F5.
# It runs on ESP32; secrets.py, boot.py and main.py are preserved.

import os
import gc
import hashlib
import binascii

UPDATE_ROLE = __ROLE__
UPDATE_VERSION = __VERSION__
EXPECTED_IP = __EXPECTED_IP__
FILES = __FILES__


def _checksum(path):
    try:
        with open(path, 'rb') as stream:
            digest = hashlib.sha256()
            while True:
                chunk = stream.read(1024)
                if not chunk:
                    break
                digest.update(chunk)
        return binascii.hexlify(digest.digest()).decode()
    except OSError:
        return None


def _update():
    import secrets
    actual_ip = getattr(secrets, 'STATIC_IP', None)
    print('UPDATE:', UPDATE_ROLE, 'version:', UPDATE_VERSION, 'board IP:', actual_ip)
    if actual_ip != EXPECTED_IP:
        raise RuntimeError('Wrong board: open the updater for this board role')
    if UPDATE_ROLE == 'gate':
        from machine import Pin
        Pin(15, Pin.OUT, value=0)
    try:
        os.mkdir('/lib')
    except OSError:
        if not os.stat('/lib')[0] & 0x4000:
            raise
    for target, expected, chunks in FILES:
        if _checksum(target) == expected:
            print('Unchanged:', target)
            continue
        temporary = target + '.upload'
        with open(temporary, 'wb') as stream:
            for encoded in chunks:
                stream.write(binascii.a2b_base64(encoded))
        if _checksum(temporary) != expected:
            raise RuntimeError('Verification failed: ' + target)
        os.rename(temporary, target)
        print('Updated:', target)
        gc.collect()
    print('SUCCESS: firmware', UPDATE_VERSION, 'for', UPDATE_ROLE)
    print('Configuration and boot files preserved; WiFi SOURCE:', getattr(secrets, 'SOURCE', 'unset'))
    print('Close old application tabs to avoid running their cached contents.')
    print('Power-cycle the board, then in Shell run:')
    print('exec(open("/test_' + UPDATE_ROLE + '_remote_unlock.py").read())')


try:
    _update()
finally:
    del FILES
    gc.collect()
