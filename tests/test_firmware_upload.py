import importlib.util
from pathlib import Path
import unittest
import io
import sys
import types
from unittest.mock import patch


class UploadTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'tools/firmware.py'
        spec = importlib.util.spec_from_file_location('upload_test', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_generated_device_code_has_valid_quotes_for_all_sources(self):
        for role in ('gate', 'house'):
            for source in (None, 'auto', 'router', 'ap'):
                commands = self.module.upload_commands(role, '/dev/test', source)
                for i, command in enumerate(commands):
                    if command == 'exec':
                        compile(commands[i + 1], '<device>', 'exec')

    def test_source_update_preserves_credentials_and_is_valid_python(self):
        original = "WIFI_PASSWORD = 'dummy-test-value'\nSOURCE = 'ap'\nSTATIC_IP = '192.168.1.237'\n"
        result = []
        class Capture(io.StringIO):
            def close(self):
                result.append(self.getvalue())
                super().close()
        def open_file(path, mode='r'):
            return Capture() if mode == 'w' else io.StringIO(original)
        modules = {'machine': types.ModuleType('machine'),
                   'os': types.SimpleNamespace(mkdir=lambda p: None),
                   'secrets': types.SimpleNamespace(STATIC_IP='192.168.1.237', PEER_IP='192.168.1.238')}
        with patch.dict(sys.modules, modules), patch('builtins.open', open_file):
            exec(self.module.preflight('gate', 'auto'), {})
        settings = {}
        exec(result[0], settings)
        self.assertEqual(settings['WIFI_PASSWORD'], 'dummy-test-value')
        self.assertEqual(settings['SOURCE'], 'auto')
        self.assertEqual(result[0].count('SOURCE ='), 1)

    def test_manifest_preserves_secrets_and_boot_files(self):
        for role in ('gate', 'house'):
            targets = self.module.files_for(role)
            self.assertNotIn('secrets.py', targets)
            self.assertNotIn('boot.py', targets)
            self.assertNotIn('main.py', targets)
            self.assertIn('lib/unlock_notice.py', targets)
            self.assertEqual('lib/tag_presence.py' in targets, role == 'gate')
