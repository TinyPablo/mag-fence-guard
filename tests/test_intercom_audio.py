"""Host-side transport and lifecycle checks; run with python3 -m unittest discover."""

import array
import errno
import importlib.util
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch


class Device:
    RX = 0
    TX = MONO = 1

    def __init__(self, *args, **kwargs):
        self.closed = False
        self.callback = None
        self.buffer = None
        self.written = []

    def irq(self, callback):
        self.callback = callback

    def readinto(self, buffer):
        self.buffer = buffer

    def write(self, buffer):
        self.written.append(bytes(buffer))

    def deinit(self):
        self.closed = True


class Socket:
    def __init__(self):
        self.incoming = []
        self.sent = []
        self.closed = False
        self.fail_send = False

    def bind(self, address):
        pass

    def setblocking(self, value):
        pass

    def sendto(self, packet, peer):
        if self.fail_send:
            raise OSError(12)
        self.sent.append(bytes(packet))

    def recvfrom(self, size):
        if not self.incoming:
            raise OSError(errno.EAGAIN)
        packet, peer = self.incoming.pop(0)
        return packet[:size], peer

    def close(self):
        self.closed = True


class Chime:
    def __init__(self):
        self.released = False

    def release(self):
        self.released = True

    def resume(self):
        self.released = False


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.socket = Socket()
        sock_module = types.SimpleNamespace(AF_INET=2, SOCK_DGRAM=2,
                                            socket=lambda *a: self.socket)
        overrides = {
            'socket': sock_module,
            'machine': types.SimpleNamespace(Pin=lambda n: n, I2S=Device),
            'uarray': array,
            'secrets': types.SimpleNamespace(PEER_IP='192.168.1.2', PEER_PORT=5006),
        }
        source = Path(__file__).resolve().parents[1] / 'firmware/gate-node/lib/intercom_audio.py'
        spec = importlib.util.spec_from_file_location('audio_under_test', source)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, overrides), patch.object(sys, "dont_write_bytecode", True):
            with patch('time.ticks_ms', lambda: 1000, create=True), \
                 patch('time.ticks_diff', lambda a, b: a - b, create=True):
                spec.loader.exec_module(self.module)
        self.chime = Chime()
        self.voice = self.module.Voice(self.chime)
        self.session = types.SimpleNamespace(
            state='RINGING', call_id=b'a' * 24, role='house',
            link=types.SimpleNamespace(wlan=types.SimpleNamespace(isconnected=lambda: True)))
        self.session.end = lambda: setattr(self.session, 'state', 'IDLE')

    def test_microphone_only_during_talking_and_resources_closed(self):
        self.voice.service(self.session)
        self.assertIsNone(self.voice.mic)
        self.session.state = 'TALKING'
        self.voice.service(self.session)
        mic, speaker = self.voice.mic, self.voice.speaker
        self.assertTrue(self.chime.released)
        self.session.state = 'IDLE'
        self.voice.service(self.session)
        self.assertTrue(mic.closed and speaker.closed and self.socket.closed)
        self.assertFalse(self.chime.released)
        self.assertIsNone(self.voice.mic)

    def test_receive_filters_session_peer_and_sequence(self):
        self.session.state = 'TALKING'
        self.voice.service(self.session)
        def packet(key, sequence):
            return key + struct.pack('<H', sequence) + bytes(512)
        peer = ('192.168.1.2', 5006)
        self.socket.incoming = [(packet(b'b' * 24, 1), peer),
                                (packet(b'a' * 24, 2), ('192.168.1.3', 5006)),
                                (packet(b'a' * 24, 2), peer),
                                (packet(b'a' * 24, 1), peer)]
        self.voice.poll()
        self.assertEqual(self.voice.received, 1)
        self.assertEqual(len(self.voice.speaker.written), 1)
        self.socket.incoming = [(packet(b'a' * 24, 2), peer)]
        self.voice.poll()
        self.assertEqual(self.voice.received, 1)

    def test_enomem_send_does_not_terminate_control(self):
        self.session.state = 'TALKING'
        self.voice.service(self.session)
        self.socket.fail_send = True
        self.voice.mic.buffer[0] = 65536
        self.voice.mic_done(self.voice.mic)
        self.voice.service(self.session)
        self.assertTrue(self.voice.running)
        self.assertEqual(self.voice.send_errors, 1)
        self.assertEqual(self.session.state, 'TALKING')

    def test_send_preserves_pcm_conversion_and_session_header(self):
        self.session.state = 'TALKING'
        self.voice.service(self.session)
        self.voice.samples[0] = 65536
        self.voice.samples[1] = -65536
        self.voice.mic_done(self.voice.mic)
        self.voice.service(self.session)
        packet = self.socket.sent[0]
        self.assertEqual(len(packet), 538)
        self.assertEqual(packet[:24], self.session.call_id)
        self.assertEqual(struct.unpack_from('<hh', packet, 26), (1, -1))
        self.assertEqual(self.voice.mic_callbacks, 1)

    def test_idle_also_reports_audio_state(self):
        self.voice.stats_at = -5000
        with patch('builtins.print') as output:
            self.voice.service(self.session)
        self.assertTrue(any('VOICE status:' in str(c) for c in output.call_args_list))
        self.assertIsNone(self.voice.mic)

    def test_init_failure_restores_chime_and_ends_call(self):
        self.session.state = 'TALKING'
        with patch.object(self.module, 'I2S', side_effect=OSError(12)):
            self.voice.service(self.session)
        self.assertFalse(self.voice.running)
        self.assertFalse(self.chime.released)
        self.assertTrue(self.socket.closed)
        self.assertEqual(self.session.state, 'IDLE')


if __name__ == '__main__':
    unittest.main()
