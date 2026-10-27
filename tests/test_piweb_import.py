"""Synthetic archive integration: existing lab gates remain authoritative."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from llm_authoring.core import Error, freeze, read_json, write_json
from llm_authoring.manual import prepare_model
from llm_authoring.workspace import create_workspace, choose_domain, choose_type
from test_core import question

RECIPE = Path(__file__).resolve().parents[1] / 'skills/llm-authoring-workflow/references/automation-recipes/piweb-import.py'
spec = importlib.util.spec_from_file_location('piweb_import', RECIPE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class PiWebImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        workspace = Path(self.temp.name) / 'workspace'
        create_workspace(workspace)
        self.root = workspace / 'question-001'
        task = read_json(self.root / 'TASK.json'); task['platform_checks_required'] = False
        write_json(self.root / 'TASK.json', task)
        request = read_json(self.root / 'REQUEST.json'); request.pop('selection_schema', None)
        write_json(self.root / 'REQUEST.json', request)
        choose_domain(self.root, '计算机科学'); choose_type(self.root, '分析决策类')
        self.q = question(); self.q['task_id'] = 'question-001'; freeze(self.root, self.q)
        self.directory = Path(self.temp.name) / 'attempt'; self.directory.mkdir()
        self.raw = b'# Synthetic\r\n\r\nComplete answer.\n'
        (self.directory / 'reply.md').write_bytes(self.raw)
        (self.directory / 'session.json').write_bytes(b'{}')
        self.result = dict(role='seed', version='r0001', promptHash=bridge.digest(self.q['prompt'].encode()),
                           replyHash=bridge.digest(self.raw), sessionHash=bridge.digest(b'{}'), sessionId='synthetic', stopReason='stop')
        write_json(self.directory / 'result.json', self.result)
        write_json(self.directory / 'create-intent.json', self.result)
        write_json(self.directory / 'create-receipt.json', dict(sessionId='synthetic'))

    def test_import_is_exact_and_resume_preserves_original(self):
        self.assertEqual(bridge.import_archive(self.root, self.directory)['status'], 'imported')
        again = bridge.import_archive(self.root, self.directory)
        self.assertEqual(again['status'], 'already_imported')
        self.assertEqual(Path(again['reply_file']).read_bytes(), self.raw)

    def test_crash_after_slot_write_resumes_existing_lab_import(self):
        with patch.object(bridge, 'import_model', side_effect=RuntimeError('interrupted')):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                bridge.import_archive(self.root, self.directory)
        self.assertEqual(bridge.import_archive(self.root, self.directory)['status'], 'imported')

    def test_tamper_and_wrong_version_stop_before_prepare(self):
        self.result['version'] = 'r9999'; write_json(self.directory / 'result.json', self.result)
        with patch.object(bridge, 'prepare_model') as prepare:
            with self.assertRaisesRegex(Error, '版本'): bridge.import_archive(self.root, self.directory)
            prepare.assert_not_called()
        self.result['version'] = 'r0001'; write_json(self.directory / 'result.json', self.result)
        (self.directory / 'reply.md').write_bytes(b'changed')
        with self.assertRaisesRegex(Error, '哈希'): bridge.import_archive(self.root, self.directory)

    def test_existing_different_slot_is_never_replaced(self):
        slot = Path(prepare_model(self.root, 'seed')['input_file']); slot.write_bytes(b'Existing answer')
        with self.assertRaisesRegex(Error, '已有不同内容'): bridge.import_archive(self.root, self.directory)
        self.assertEqual(slot.read_bytes(), b'Existing answer')

    def test_gpt_cannot_bypass_seed_gate_and_manual_task_rejected(self):
        self.result['role'] = 'gpt'
        for name in ('result.json', 'create-intent.json'): write_json(self.directory / name, self.result)
        with self.assertRaisesRegex(Error, 'Seed'): bridge.import_archive(self.root, self.directory)
        task = read_json(self.root / 'TASK.json'); task['platform_checks_required'] = True; write_json(self.root / 'TASK.json', task)
        with self.assertRaisesRegex(Error, '自动化'): bridge.import_archive(self.root, self.directory)
