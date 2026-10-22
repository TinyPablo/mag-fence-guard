import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class ServiceModeTests(unittest.TestCase):
    def run_guard(self, role, button_value):
        clock = [0]
        outputs = []
        class Pin:
            OUT = 1
            IN = 0
            PULL_UP = 2
            def __init__(self, number, *args, **kwargs):
                self.number = number
                outputs.append((number, kwargs.get('value')))
            def value(self):
                return button_value(clock[0])
        path = Path(__file__).resolve().parents[1] / 'firmware/gate-node/lib/service_mode.py'
        spec = importlib.util.spec_from_file_location('service_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'machine': types.SimpleNamespace(Pin=Pin)}), \
             patch('time.ticks_ms', lambda: clock[0], create=True), \
             patch('time.ticks_diff', lambda a, b: a-b, create=True), \
             patch('time.sleep_ms', lambda ms: clock.__setitem__(0, clock[0]+ms), create=True):
            spec.loader.exec_module(module)
        return module.service_requested(role), outputs, clock[0]

    def test_held_button_enters_service_on_each_role(self):
        for role in ('gate','house'):
            service, pins, elapsed = self.run_guard(role, lambda now: 0)
            self.assertTrue(service)
            self.assertEqual(elapsed, 3000)
            self.assertEqual((15, 0) in pins, role == 'gate')

    def test_unpressed_or_short_press_starts_normally(self):
        for value in (lambda now: 1, lambda now: int(now >= 1000), lambda now: int(now < 1000)):
            self.assertFalse(self.run_guard('gate', value)[0])

    def test_guard_precedes_heavy_app_initialization(self):
        root = Path(__file__).resolve().parents[1]
        for role in ('gate', 'house'):
            path = root / ('firmware/'+role+'-node/test_'+role+'_remote_unlock.py')
            tree = ast.parse(path.read_text())
            gate = next(i for i,n in enumerate(tree.body) if isinstance(n,ast.If) and
                        isinstance(n.test,ast.Call) and getattr(n.test.func,'id',None)=='service_requested')
            self.assertTrue(any(isinstance(n,ast.Raise) for n in tree.body[gate].body))
            self.assertFalse(any(isinstance(n,ast.Assign) and isinstance(n.value,ast.Call)
                                 for n in tree.body[:gate]))
