"""Check shared unlock sequencing without initializing hardware."""

import ast
from pathlib import Path
import unittest
import types


class UnlockPathTests(unittest.TestCase):
    def test_session_ends_before_relay_and_buzzer(self):
        path = Path(__file__).resolve().parents[1] / 'firmware/gate-node/test_gate_remote_unlock.py'
        module = ast.parse(path.read_text())
        function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'unlock')
        events = []
        env = {
            'session': types.SimpleNamespace(finish=lambda: events.append('end')),
            'chime': types.SimpleNamespace(buzz=lambda ms: events.append(('buzz', ms))),
            'notice': types.SimpleNamespace(notify=lambda source: events.append(('notice', source))),
            'ticks_ms': lambda: 1000, 'ticks_add': lambda a, b: a + b,
            'UNLOCK_MS': 3000, 'set_relay': lambda v: events.append(('relay', v)),
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<unlock>', 'exec'), env)
        env['unlock']('rfid:ABC')
        self.assertEqual(events, ['end', ('relay', True), ('buzz', 3000), ('notice', 'rfid:ABC')])
        self.assertEqual(env['unlock_until'], 4000)
        self.assertTrue(env['unlocked'])
