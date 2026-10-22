"""Identify the loaded application and module versions at every startup."""

import sys

VERSION = "0.4.0"


def report(role, script_version):
    names = ["lib.remote_link", "lib.intercom_session", "lib.intercom_audio", "chime"]
    if role == "gate":
        names += ["lib.mfrc522", "lib.rfid_debug", "lib.rfid_recovery"]
    print("FIRMWARE: Mag Fence Guard | role=%s | script=%s | shared=%s" %
          (role, script_version, VERSION))
    compatible = script_version == VERSION
    for name in names:
        module = sys.modules.get(name)
        version = getattr(module, "MODULE_VERSION", "unknown")
        print("  %s: %s" % (name, version))
        compatible = compatible and version == VERSION
    if not compatible:
        raise RuntimeError("Mixed firmware versions; upload all files from the same release and restart")
