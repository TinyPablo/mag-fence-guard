import importlib.util
from pathlib import Path
import unittest
import io
import os
import tempfile
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


class ThonnyBundleTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'tools/firmware.py'
        spec = importlib.util.spec_from_file_location('thonny_builder_test', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def run_bundle(self, role, board_ip, root):
        rendered = self.module.render_update(role)
        real_open = open
        def mapped(path):
            return root / str(path).lstrip('/')
        def board_open(path, *args, **kwargs):
            return real_open(mapped(path), *args, **kwargs)
        fake_os = types.SimpleNamespace(
            mkdir=lambda path: os.mkdir(mapped(path)),
            stat=lambda path: os.stat(mapped(path)),
            rename=lambda src, dst: os.replace(mapped(src), mapped(dst)))
        class Pin:
            OUT = 1
            def __init__(self, *args, **kwargs):
                pass
        modules = {'os': fake_os, 'machine': types.SimpleNamespace(Pin=Pin),
                   'secrets': types.SimpleNamespace(STATIC_IP=board_ip, SOURCE='auto')}
        with patch.dict(sys.modules, modules), patch('builtins.open', board_open),              patch('builtins.print') as output:
            exec(rendered, {})
        return output

    def test_each_bundle_writes_verified_files_and_preserves_settings(self):
        for role in ('gate', 'house'):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                protected = ('secrets.py', 'boot.py', 'main.py')
                for name in protected:
                    (root / name).write_text('preserve me')
                self.run_bundle(role, self.module.ROLE_IP[role], root)
                for target, source in self.module.files_for(role).items():
                    self.assertEqual((root / target).read_bytes(), source.read_bytes())
                for name in protected:
                    self.assertEqual((root / name).read_text(), 'preserve me')
                output = self.run_bundle(role, self.module.ROLE_IP[role], root)
                self.assertFalse(any(call.args[0] == 'Updated:' for call in output.call_args_list))

    def test_wrong_board_stops_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(RuntimeError, 'Wrong board'):
                self.run_bundle('gate', '192.168.1.238', root)
            self.assertEqual(list(root.iterdir()), [])
