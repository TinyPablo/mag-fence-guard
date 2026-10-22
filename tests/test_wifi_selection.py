"""Check known-AP selection by signal and filtering of unrelated networks."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class WifiSelectionTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'firmware/gate-node/lib/remote_link.py'
        spec = importlib.util.spec_from_file_location('wifi_under_test', path)
        self.module = importlib.util.module_from_spec(spec)
        fake_secrets = types.SimpleNamespace(WIFI_SSID='test', WIFI_PASSWORD='',
                                            STATIC_IP='192.168.1.237', PEER_IP='192.168.1.238', SOURCE='auto')
        with patch.dict(sys.modules, {'network': types.SimpleNamespace(), 'secrets': fake_secrets}), \
             patch.object(sys, 'dont_write_bytecode', True), \
             patch('time.ticks_ms', lambda: 0, create=True), \
             patch('time.ticks_diff', lambda a, b: a - b, create=True):
            spec.loader.exec_module(self.module)
        self.router = bytes.fromhex('D4B709CA4536')
        self.ap = bytes.fromhex('088AF1D9D45E')

    def row(self, bssid, rssi, ssid=b'test'):
        return (ssid, bssid, 3, rssi, 3, False)

    def test_strongest_first(self):
        choices = self.module.select_access_points([
            self.row(self.router, -75), self.row(self.ap, -42)], 'test')
        self.assertEqual([c[0] for c in choices], ['ap', 'router'])
        choices = self.module.select_access_points([
            self.row(self.router, -35), self.row(self.ap, -65)], 'test')
        self.assertEqual(choices[0][0], 'router')

    def test_only_one_visible(self):
        for bssid, name in ((self.router, 'router'), (self.ap, 'ap')):
            choices = self.module.select_access_points([self.row(bssid, -50)], 'test')
            self.assertEqual(len(choices), 1)
            self.assertEqual(choices[0][0], name)

    def test_unknown_and_other_ssid_ignored(self):
        choices = self.module.select_access_points([
            self.row(bytes(6), -20), self.row(self.ap, -10, b'other')], 'test')
        self.assertEqual(choices, [])

    def test_duplicate_bssid_keeps_strongest(self):
        choices = self.module.select_access_points([
            self.row(self.router, -70), self.row(self.router, -50)], 'test')
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0][2], -50)


if __name__ == '__main__':
    unittest.main()
