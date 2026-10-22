"""Check repeated chime timing and immediate speaker release."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Speaker:
    TX = MONO = 1

    def __init__(self, *args, **kwargs):
        self.closed = False
        self.written = 0

    def write(self, data):
        self.written += len(data)
        return len(data)

    def deinit(self):
        self.closed = True


class ChimeTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        path = Path(__file__).resolve().parents[1] / 'firmware/house-node/chime.py'
        spec = importlib.util.spec_from_file_location('chime_under_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'machine': types.SimpleNamespace(Pin=lambda n: n, I2S=Speaker)}), \
             patch.object(sys, 'dont_write_bytecode', True), \
             patch('time.ticks_ms', lambda: self.now, create=True), \
             patch('time.ticks_diff', lambda a, b: a - b, create=True), \
             patch('time.ticks_add', lambda a, b: a + b, create=True):
            spec.loader.exec_module(module)
        self.chime = module.Chime()

    def test_repeats_after_gap_and_stops_at_30_seconds(self):
        self.chime.ring(repeat=True)
        for _ in range(110):
            self.chime.poll()
        speaker = self.chime.speaker
        first = speaker.written
        self.assertGreater(first, 0)
        self.now = 899
        self.chime.poll()
        self.assertEqual(speaker.written, first)
        self.now = 900
        self.chime.poll()
        self.assertGreater(speaker.written, first)
        self.now = 30000
        self.chime.poll()
        self.assertTrue(speaker.closed)
        self.assertFalse(self.chime.repeating)

    def test_stop_flushes_and_next_ring_reopens_speaker(self):
        self.chime.ring(repeat=True)
        self.chime.poll()
        previous = self.chime.speaker
        self.chime.stop()
        self.assertTrue(previous.closed)
        self.chime.poll()
        self.assertIsNone(self.chime.speaker)
        self.chime.ring(repeat=True)
        self.assertIsNot(self.chime.speaker, previous)


if __name__ == '__main__':
    unittest.main()
