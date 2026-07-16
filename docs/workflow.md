# Git workflow

- Branch naming: `test/<topic>` per experiment, e.g. `test/rfid-read`,
  `test/button-led`, `test/esp32-link`, `test/audio-loopback`.
- Foundational/documentation work (scaffolding, journal entries, BOM) happens
  directly on `main` - branches are for actual firmware/hardware experiments.
- Open a self-PR from the branch to `main` even when working solo; the PR
  description doubles as the experiment log (what was tested, what worked or
  failed).
- After merging, delete the branch. The PR itself (commits + description)
  stays visible under GitHub's closed-PR list, so the record isn't lost.
- Optional milestone tags on `main` at working states, e.g. `v0.1-rfid-ok`,
  `v0.2-audio-ok`, `v0.3-integrated`.
- English only in code, commits, and docs. Comments only for non-obvious
  "why," not restating what the code does.
