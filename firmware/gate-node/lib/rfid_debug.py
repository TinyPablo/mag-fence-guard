"""Manual RC522 inspection after stopping the gate script; never unlocks."""

from time import ticks_ms, ticks_diff, sleep_ms

REGISTERS = (
    ("Version", 0x37), ("Command", 0x01), ("ComIEn", 0x02),
    ("ComIrq", 0x04), ("Error", 0x06), ("Status1", 0x07),
    ("Status2", 0x08), ("FIFOLevel", 0x0A), ("Control", 0x0C),
    ("BitFraming", 0x0D), ("TxControl", 0x14), ("TMode", 0x2A),
    ("TPrescaler", 0x2B), ("TReloadH", 0x2C), ("TReloadL", 0x2D),
)


def status(reader):
    print("RC522 snapshot (no reset)")
    result = {}
    for name, address in REGISTERS:
        value = reader._rreg(address)
        result[name] = value
        print("  %s: 0x%02X" % (name, value))
    print("  RST pin:", reader.rst.value())
    if result["Version"] in (0x00, 0xFF):
        print("  Version is 00/FF: check power/SPI; this alone is not a diagnosis.")
    return result


def reset(reader, hardware=False):
    print("Manual RC522 reset:", "RST pin" if hardware else "software command")
    if hardware:
        reader.rst.value(0)
        sleep_ms(10)
        reader.rst.value(1)
        sleep_ms(50)
    # init() resets and restores the existing reader configuration.
    reader.init()
    reader.disarm_irq()
    print("RC522 reinitialized; run rfid_probe() to test reads without unlocking.")
    return status(reader)


def probe(reader, seconds=10):
    if not 1 <= seconds <= 60:
        raise ValueError("seconds must be between 1 and 60")
    started = ticks_ms()
    stage = "wait"
    cycle_started = started - 200
    stage_started = started
    reads = 0
    print("RC522 probe: present/remove tags; relay and intercom remain stopped.")
    try:
        while ticks_diff(ticks_ms(), started) < seconds * 1000:
            now = ticks_ms()
            if stage == "wait" and ticks_diff(now, cycle_started) >= 200:
                reader.arm_irq()
                stage = "request"
                stage_started = cycle_started = ticks_ms()
            elif stage != "wait":
                if reader.irq_received():
                    if stage == "request":
                        reader.start_anticoll_irq()
                        stage = "uid"
                        stage_started = ticks_ms()
                    else:
                        code, uid = reader.finish_anticoll_irq()
                        if code == reader.OK:
                            reads += 1
                            print("Probe UID:", "-".join("%02X" % b for b in uid[:4]))
                        reader.disarm_irq()
                        stage = "wait"
                elif ticks_diff(now, stage_started) >= 40:
                    reader.disarm_irq()
                    stage = "wait"
            sleep_ms(5)
    finally:
        reader.disarm_irq()
        print("Probe finished; successful reads:", reads)
    return reads
