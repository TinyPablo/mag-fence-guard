"""Session-scoped UDP duplex audio with bounded buffers and nonblocking I2S."""

import errno
import gc
import socket
import struct
import uarray as array
from machine import Pin, I2S
from time import ticks_ms, ticks_diff
from secrets import PEER_IP, PEER_PORT

SAMPLES = 256
PCM_BYTES = SAMPLES * 2
HEADER = 26  # 24-byte call ID and 16-bit sequence number.
PACKET_BYTES = HEADER + PCM_BYTES
AUDIO_VERSION = "voice-v2-diagnostics"
WOULD_BLOCK = (errno.EAGAIN, getattr(errno, "EWOULDBLOCK", errno.EAGAIN))


class Voice:
    def __init__(self, chime, role="node"):
        self.chime = chime
        self.role = role
        self.mic = self.speaker = self.sock = None
        self.call_id = None
        self.running = False
        self.stats_at = ticks_ms()
        self.sent = self.received = self.dropped = self.send_errors = 0
        self.datagrams = self.rejected = self.mic_callbacks = 0
        print("VOICE module ready:", AUDIO_VERSION, "role:", role,
              "peer:", PEER_IP, "port:", PEER_PORT)

    def mic_done(self, device):
        if device is self.mic:
            self.mic_callbacks += 1
            self.mic_ready = True

    def speaker_done(self, device):
        if device is self.speaker:
            self.speaker_busy = False

    def start(self, call_id):
        self.chime.release()
        gc.collect()
        try:
            self.samples = array.array('i', [0] * SAMPLES)
            self.packet = bytearray(PACKET_BYTES)
            self.packet[:24] = call_id
            self.latest = bytearray(PCM_BYTES)
            self.playing = bytearray(PCM_BYTES)
            self.have_latest = False
            self.mic_ready = False
            self.speaker_busy = False
            self.sequence = 0
            self.last_rx_sequence = None
            self.sent = self.received = self.dropped = self.send_errors = 0
            self.datagrams = self.rejected = self.mic_callbacks = 0
            self.stats_at = ticks_ms()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(("0.0.0.0", PEER_PORT))
            self.sock.setblocking(False)
            self.mic = I2S(0, sck=Pin(5), ws=Pin(4), sd=Pin(6),
                           mode=I2S.RX, bits=32, format=I2S.MONO,
                           rate=16000, ibuf=8192)
            self.speaker = I2S(1, sck=Pin(7), ws=Pin(8), sd=Pin(9),
                               mode=I2S.TX, bits=16, format=I2S.MONO,
                               rate=16000, ibuf=4096)
            self.mic.irq(self.mic_done)
            self.speaker.irq(self.speaker_done)
            self.call_id = call_id
            self.running = True
            self.mic.readinto(self.samples)
            print("VOICE started; role:", self.role, "call:", call_id.decode(),
                  "peer:", PEER_IP, "port:", PEER_PORT)
        except Exception:
            self.stop()
            raise

    def stop(self):
        had_resources = self.running or self.mic is not None or self.sock is not None
        self.running = False
        self.call_id = None
        mic, speaker, sock = self.mic, self.speaker, self.sock
        self.mic = self.speaker = self.sock = None
        try:
            if mic is not None:
                mic.deinit()
        finally:
            try:
                if speaker is not None:
                    speaker.deinit()
            finally:
                if sock is not None:
                    sock.close()
                for name in ("samples", "packet", "rx_view", "rx", "latest", "playing"):
                    if hasattr(self, name):
                        delattr(self, name)
                gc.collect()
                self.chime.resume()
        if had_resources:
            print("VOICE stopped")

    def poll(self):
        if self.mic_ready:
            self.mic_ready = False
            struct.pack_into("<H", self.packet, 24, self.sequence)
            self.sequence = (self.sequence + 1) & 0xFFFF
            for i in range(SAMPLES):
                struct.pack_into("<h", self.packet, HEADER + i * 2, self.samples[i] >> 16)
            try:
                self.sock.sendto(self.packet, (PEER_IP, PEER_PORT))
                self.sent += 1
            except OSError:
                # UDP congestion/ENOMEM must not terminate gate control.
                self.send_errors += 1
            self.mic.readinto(self.samples)

        for _ in range(4):
            try:
                packet, address = self.sock.recvfrom(PACKET_BYTES + 1)
            except OSError as error:
                if error.args and error.args[0] in WOULD_BLOCK:
                    break
                raise
            self.datagrams += 1
            if address != (PEER_IP, PEER_PORT) or len(packet) != PACKET_BYTES:
                self.rejected += 1
                continue
            if packet[:24] != self.call_id:
                self.rejected += 1
                continue
            sequence = struct.unpack_from("<H", packet, 24)[0]
            if self.last_rx_sequence is not None:
                delta = (sequence - self.last_rx_sequence) & 0xFFFF
                if delta == 0 or delta >= 32768:
                    self.rejected += 1
                    continue
            self.last_rx_sequence = sequence
            self.received += 1
            if self.have_latest:
                self.dropped += 1
            self.latest[:] = memoryview(packet)[HEADER:PACKET_BYTES]
            self.have_latest = True
        if not self.speaker_busy and self.have_latest:
            self.playing[:] = self.latest
            self.have_latest = False
            self.speaker_busy = True
            self.speaker.write(self.playing)

    def report(self, session):
        now = ticks_ms()
        if ticks_diff(now, self.stats_at) >= 5000:
            print("VOICE status: role=%s state=%s wifi=%s running=%s "
                  "sent=%d received=%d datagrams=%d rejected=%d "
                  "mic_callbacks=%d dropped=%d send_errors=%d" %
                  (self.role, session.state, session.link.wlan.isconnected(),
                   self.running, self.sent, self.received, self.datagrams,
                   self.rejected, self.mic_callbacks, self.dropped, self.send_errors))
            self.stats_at = now

    def service(self, session):
        try:
            desired = session.state == "TALKING" and session.link.wlan.isconnected()
            if self.running and (not desired or self.call_id != session.call_id):
                self.stop()
            if desired and not self.running:
                self.start(session.call_id)
            if self.running:
                self.poll()
            self.report(session)
        except (OSError, MemoryError, ValueError) as error:
            print("VOICE error; ending call:", error)
            self.stop()
            if session.role == "house":
                session.end()
            else:
                session.finish()


MODULE_VERSION = "0.6.0"
