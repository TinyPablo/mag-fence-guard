import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


class PresenceTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'firmware/gate-node/lib/tag_presence.py'
        spec = importlib.util.spec_from_file_location('presence_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch('time.ticks_diff', lambda a, b: a - b, create=True):
            spec.loader.exec_module(module)
        self.presence = module.TagPresence()

    def test_held_tag_and_removal(self):
        self.assertTrue(self.presence.seen('A'))
        for _ in range(10):
            self.assertFalse(self.presence.seen('A'))
        for now in (0, 200, 400, 600):
            self.presence.missing(now)
        self.assertEqual(self.presence.uid, 'A')
        self.presence.missing(800)
        self.assertTrue(self.presence.seen('A'))

    def test_recovery_does_not_rearm_tag(self):
        self.presence.seen('A')
        self.presence.missing(0)
        self.presence.pause()
        self.assertFalse(self.presence.seen('A'))

    def test_different_tag_is_new(self):
        self.presence.seen('A')
        self.assertTrue(self.presence.seen('B'))
