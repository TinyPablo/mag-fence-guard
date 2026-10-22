import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


class PirExitTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        path = Path(__file__).resolve().parents[1] / 'firmware/gate-node/lib/pir_exit.py'
        spec = importlib.util.spec_from_file_location('pir_exit_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch('time.ticks_ms', lambda: self.now, create=True), \
             patch('time.ticks_diff', lambda a, b: a-b, create=True):
            spec.loader.exec_module(module)
        self.PirExit = module.PirExit

    def test_warmup_high_cannot_open_until_low_then_rising(self):
        pir = self.PirExit()
        self.assertFalse(pir.update(1, False))
        self.now = 60000
        self.assertFalse(pir.update(1, False))
        self.now = 60100
        self.assertFalse(pir.update(0, False))
        self.now = 60300
        self.assertFalse(pir.update(0, False))
        self.assertTrue(pir.update(1, False))
        self.assertFalse(pir.update(1, False))

    def test_unlocked_motion_does_not_extend_and_requires_new_low(self):
        pir = self.PirExit(0)
        pir.update(0, False)
        self.now = 200
        pir.update(0, False)
        self.assertTrue(pir.update(1, False))
        for high in (1, 0, 1, 0, 1):
            self.now += 200
            self.assertFalse(pir.update(high, True))
        self.assertFalse(pir.update(1, False))
        pir.update(0, False)
        self.now += 200
        pir.update(0, False)
        self.assertTrue(pir.update(1, False))

    def test_short_glitch_and_invalid_warmup(self):
        pir = self.PirExit(0)
        pir.update(0, False)
        self.now = 100
        self.assertFalse(pir.update(1, False))
        for value in (-1, 600001, 'zero'):
            with self.assertRaises(ValueError):
                self.PirExit(value)
