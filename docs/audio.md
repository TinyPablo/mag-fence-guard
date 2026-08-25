# Audio

Hardware: INMP441 I2S MEMS microphone + MAX98357A I2S Class-D amp + 40mm/3W/4Ω
speaker, one set per node (see `bom.md`). Both are digital I2S devices, no
analog mic preamp or line-level wiring involved.

Earlier work (single-board record/playback loopback, then live streaming,
then two-board ESP-NOW) lives on the separate, not-yet-merged
`test/audio-loopback` branch - mic and speaker plumbing worked, but
two-board ESP-NOW playback quality wasn't resolved (data arrived, sound
didn't come out clean). Paused there to build the gate-relay prototype
instead. This doc covers a new approach, testing the mic and speaker
modules independently before going back to a real ESP32-to-ESP32 link.

## WiFi + Mac relay test (`test/audio-wifi-relay` branch)

Goal: verify the mic and speaker modules one at a time, using a Mac as a
"man in the middle" - since the ESP32 has no storage of its own to save a
WAV file to, it streams raw audio over WiFi to a small TCP listener
running on a Mac, which does have storage and lets us actually listen to
what was captured. **This is a debugging harness only** - the final
gate<->house transport (ESP-NOW vs. MQTT vs. something else) is still an
open decision, unaffected by this test.

Plan:
1. Mic only: `firmware/gate-node/test_audio_wifi_mic.py` records a fixed
   3s from the INMP441 into RAM first, then sends the whole clip to
   `tools/audio-wifi-relay/mic_receiver.py` running on a Mac, which saves
   it as a `.wav`. Listen to the result to confirm the mic capture itself
   is clean, independent of any speaker issues.
2. Speaker only: once the mic recording sounds good, play that same `.wav`
   back through the MAX98357A + speaker (Mac -> ESP32 this time) to verify
   playback quality on its own.
3. Only once both check out individually: test them together, closer to
   the real two-board setup.

### Mic test wiring

Same as the earlier loopback test:

| INMP441 pin | ESP32 |
|---|---|
| VDD | 3.3V |
| GND | GND |
| L/R | GND (selects left channel) |
| WS | GPIO25 |
| SCK | GPIO26 |
| SD | GPIO33 |

### Mic test setup

1. Copy `firmware/gate-node/secrets.py.example` to `secrets.py` in the same
   folder, fill in your WiFi SSID/password and your Mac's local IP
   (`SERVER_IP`) - `secrets.py` is gitignored, real credentials never get
   committed.
2. On the Mac: `python3 tools/audio-wifi-relay/mic_receiver.py` - it
   listens on port 5005 and waits.
3. On the ESP32 (Thonny): upload `secrets.py` and `test_audio_wifi_mic.py`,
   run it. It joins WiFi, connects to the Mac, records 3s from the mic
   into RAM, then sends the whole clip over and disconnects.
4. The Mac script saves `tools/audio-wifi-relay/recordings/mic-<timestamp>.wav`
   (gitignored - these are personal recordings, not project content) and
   prints the path. Play it back to judge quality.

**Debugging note:** the first attempts (8s, then 3s) stalled after sending
only part of the first chunk - per-chunk print statements showed
`mic.readinto()` succeeding but `sock.write()` never completing for the
second chunk, and the Mac side received far fewer bytes than were
supposedly sent. Root cause: ESP32's default WiFi power-save (modem-sleep)
puts the radio to sleep between transmissions, which stalls a tight
I2S-read + socket-write loop for multiple seconds at a time. Fixed by
disabling it right after connecting: `wlan.config(pm=network.WLAN.PM_NONE)`.

With power-save disabled, the connection no longer froze, but per-chunk
timing (added via `ticks_ms()`/`ticks_diff()` around each `readinto()` and
`write()` call) showed 3s of audio taking ~13.5s wall-clock to send -
`write()` calls were mostly fast (1-2ms) but frequently spiked to
200-500ms (once even ~2s). Tried disabling Nagle
(`sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)`) suspecting a
Nagle/delayed-ACK interaction - wall-clock time barely changed (~12.4s),
so that wasn't the (sole) cause; more likely just normal WiFi/TCP jitter
and small send-buffer stalls on this hardware, which we didn't chase
further because of what it was doing to the recording itself (next
paragraph). Left `TCP_NODELAY` set since it doesn't hurt.

The real problem: interleaving `sock.write()` inside the recording loop
meant every stall (100ms-2s) left the I2S peripheral's DMA buffer
(`ibuf=20000`, only ~5 chunks of slack) with nowhere to put incoming
samples, so it silently overwrote/dropped whatever hadn't been read yet.
The recording still produced the right total byte count (192512 bytes,
matching a nominal 3.01s clip), but those bytes were disjoint snapshots
scattered across the full ~12s the run actually took, not one continuous
3s clip - so played back at a fixed 16kHz it sounded sped up/chipmunk'd,
with chunks of real time silently skipped.

**Fix: record-then-send.** Capture the whole clip into a list of small
(`CHUNK_BYTES`-sized) buffers first, in a tight loop with *no* network
calls at all - nothing can stall it, so the mic is read at the true sample
rate throughout and the recording is genuinely continuous. Only after
recording finishes does the script iterate over the buffered chunks and
send them over the socket; that phase can take as long as it wants (it
already did, before, and it never affected content) since it's just moving
already-captured bytes, not sampling live. Splitting into many small
buffers instead of one ~188KB block also sidesteps the `MemoryError` a
single large buffer hit in the original loopback test.

Audio config is unchanged from the working loopback test: `rate=16000`,
`bits=32`, `format=I2S.MONO` - INMP441 outputs 24-bit samples left-justified
in the 32-bit word, which is why `bits=32` is needed even though the mic
itself isn't a 32-bit part. Saving those same raw bytes into a WAV with
`sampwidth=4` is bit-for-bit consistent with what the ESP32 side reads/writes,
so no format conversion is happening here - just relaying the same bytes.

### Speaker test

Not written yet - happens after the mic recording is confirmed good. Will
send the verified `.wav` from the Mac back to the ESP32 (amp on
BCLK=GPIO14/LRC=GPIO4/DIN=GPIO27, same as the streaming test) to play, so
we're judging playback with real known-good audio rather than a synthetic
tone.

## Open

- Duplex mode for the real gate<->house intercom (push-to-talk vs.
  full-duplex vs. VOX) is a separate, still-open decision - see
  `CONTEXT.md`. Neither the loopback nor this WiFi-relay test resolves it;
  both are just proving out mic/speaker plumbing in isolation.
- ESP32<->ESP32 transport (ESP-NOW vs. MQTT vs. direct socket) - still
  open, this WiFi+Mac setup is a debug tool, not a transport candidate
  (no Mac in the final installation).
