# mag-fence-guard

Electromagnetic gate lock controller for a rural property, with RFID access,
a two-way audio intercom between the gate and the house, and an indoor
button to open the gate remotely.

## How it works

- A house-side button unlocks the gate for ~10-15s.
- A gate-side button triggers a chime in the house and opens a two-way
  audio channel between the gate and the house.
- Family members get RFID tags for direct access.
- Two ESP32 nodes: one at the gate (`firmware/gate-node/`), one in the
  house (`firmware/house-node/`).

## Status

Early build phase. Power cable prepped, RFID testing starting next. See
`docs/journal.md` for the build log.

## Docs

- [`docs/power.md`](docs/power.md) - power chain and fail-safe behavior
- [`docs/bom.md`](docs/bom.md) - parts list
- [`docs/workflow.md`](docs/workflow.md) - git branching/PR conventions
- [`docs/journal.md`](docs/journal.md) - chronological build log with photos
- [`CONTEXT.md`](CONTEXT.md) - project priming notes for AI-assisted sessions

## License

See [`LICENSE`](LICENSE).
