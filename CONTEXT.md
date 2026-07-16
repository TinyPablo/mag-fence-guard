# CONTEXT.md - priming file for AI sessions

Paste this file (or point your assistant at it) at the start of a new
conversation about this project, then say which branch/module you're
currently focused on. This exists so context doesn't have to be rebuilt
from scratch every session.

## Project summary

Mag Fence Guard is an electromagnetic gate lock at a rural property,
controlled from the house, with a two-way audio intercom and RFID access
for family. Two ESP32 nodes: one at the gate/pole (~20m from the house,
cable + conduit already run), one in the house.

Flow: a house-side button unlocks the gate for ~10-15s. A gate-side button
lets a visitor (e.g. a neighbor) trigger a chime heard in the house and
open a two-way audio channel with whoever is at the gate. Family members
get RFID tags for direct access without going through the house.

## Fixed decisions

- Electromagnet is fail-safe: power loss = gate unlocked. Not a fire-safety
  concern for this property. A battery buffer between the PSU and the
  magnet (to keep it locked during outages) is a possible future addition,
  not current scope.
- RFID: MFRC522 reader, already soldered, 6 tags total (13.56MHz).
- Audio hardware: INMP441 I2S MEMS mic + MAX98357 I2S Class-D amp +
  40mm/3W/4Ω speaker - one full set per node (gate + house).
- Power chain: 230VAC → 12VDC PSU → relay for the magnet, plus a step-down
  converter to 5V for the ESP32s.
- Enclosure: PETG (not PLA) for outdoor durability, gaskets/cable glands
  planned. First 3D-enclosure project for the builder - expected to be the
  hardest part.
- Repo/git workflow: mono-repo, branches named `test/<topic>` per
  experiment, self-PR before merging to main, branch deleted after merge
  (the PR itself preserves the experiment record). Optional milestone tags
  on main for working states.
- Conventions: English only in code/commits/docs. Comments only for
  non-obvious "why," not restating what the code does. BOM entries list
  product names + basic specs, no purchase links (they expire).

## Open decisions - do not assume these are resolved

- Audio duplex mode: push-to-talk was rejected for the outdoor/visitor side
  (they won't know to hold a button); full-duplex vs. VOX vs. some
  asymmetric scheme is still to be settled by testing mic/speaker feedback
  behavior.
- ESP32↔ESP32 transport: ESP-NOW vs. MQTT vs. direct UDP/WebSocket -
  undecided, depends on latency/reliability testing.
- RFID whitelist management: hardcoded UIDs in firmware vs. an enrollment
  mode - undecided.

## Current status / progress log

- **Done:** Prepared the 20m power cable for the gate run - cut it to
  length, soldered it to the 230VAC PSU input leads using heat-shrink
  tubing, verified which conductor is phase vs. neutral before connecting,
  and sealed the splice tightly with insulating tape.
- **Next:** Test RFID (MFRC522) first - likely branch `test/rfid-read`.

## How this file gets used

Keep the "Current status / progress log" section up to date as work
happens - that's the fastest-changing part. The sections above it change
rarely and only when a real design decision is made or revisited.
