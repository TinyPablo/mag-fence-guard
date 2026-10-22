import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Link:
    def __init__(self):
        self.online = True
        self.wlan = types.SimpleNamespace(isconnected=lambda: self.online)
        self.sent = []

    def send(self, data):
        self.sent.append(data)


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        path = Path(__file__).resolve().parents[1] / 'firmware/gate-node/lib/unlock_notice.py'
        spec = importlib.util.spec_from_file_location('notice_test', path)
        module = importlib.util.module_from_spec(spec)
        fake = types.SimpleNamespace(valid_id=lambda key: len(key) == 24)
        with patch.dict(sys.modules, {'lib': types.ModuleType('lib'), 'lib.intercom_session': fake}), \
             patch('time.ticks_ms', lambda: self.now, create=True), \
             patch('time.ticks_diff', lambda a, b: a-b, create=True):
            spec.loader.exec_module(module)
        self.gl, self.hl = Link(), Link()
        self.gate = module.UnlockNotice(self.gl, 'gate')
        self.house = module.UnlockNotice(self.hl, 'house')

    def event(self):
        self.house.poll()
        self.gate.receive(self.hl.sent[-1])
        self.gate.notify('rfid:ABC')
        self.gate.poll()
        return self.gl.sent[-1]

    def test_fresh_event_once_and_ack(self):
        event = self.event()
        self.assertEqual(self.house.receive(event), b'rfid:ABC')
        self.assertIsNone(self.house.receive(event))
        self.gate.receive(self.hl.sent[-1])
        self.assertIsNone(self.gate.pending)

    def test_pir_source_is_delivered(self):
        self.house.poll()
        self.gate.receive(self.hl.sent[-1])
        self.gate.notify('pir')
        self.gate.poll()
        self.assertEqual(self.house.receive(self.gl.sent[-1]), b'pir')

    def test_expired_event_does_not_ring(self):
        event = self.event()
        self.now += 1000
        self.assertIsNone(self.house.receive(event))

    def test_offline_unlock_is_not_queued(self):
        self.gate.notify('house')
        self.assertIsNone(self.gate.pending)
        self.event()
        self.gl.online = False
        self.gate.poll()
        self.assertIsNone(self.gate.pending)
        self.gl.online = True
        previous = len(self.gl.sent)
        self.gate.poll()
        self.assertEqual(len(self.gl.sent), previous)

    def test_retries_expire_before_reconnection(self):
        self.event()
        self.now += 800
        self.gate.poll()
        self.assertIsNone(self.gate.pending)
