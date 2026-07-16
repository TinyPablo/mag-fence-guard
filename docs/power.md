# Power chain

## Path

230VAC mains → PSU → 12VDC → relay (switches the magnet) → step-down converter → 5V for the gate-node ESP32.

The house-node ESP32 is powered separately - normally from a wall outlet - and is not part of this chain.

## Power supply

**Zasilacz LED 12V 36W** - waterproof/hermetic (IP67), narrow/slim form factor, designed for LED strips. Output: 12VDC, 36W.

Chosen originally for LED-strip use, but its IP67 rating is convenient here too since the gate-side electronics live outdoors - though the enclosure still needs to protect the rest of the electronics independently (see `hardware/enclosure/`).

## Fail-safe behavior

The electromagnet is fail-safe: if power is lost (mains outage or a cut cable), the gate unlocks. Not a fire-safety concern for this property. Confirmed 2026-07-16.

**Future consideration:** a battery buffer between the PSU and the magnet, to keep the gate locked through a power outage instead of fail-safe-opening. Not current scope - noted here so it isn't lost.

## Build log

- **2026-07-16:** Prepared the 20m power cable for the gate run - cut to length, soldered to the PSU input leads with heat-shrink tubing, verified phase vs. neutral before connecting, sealed the splice tightly with insulating tape. Photo pending in `docs/journal.md`.
