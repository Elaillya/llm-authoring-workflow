"""Synthetic manual replies only; no official UI or paid-model acceptance claim."""
import copy
import json
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from llm_authoring.core import (ALL_ROLES, Error, ROLES, active_question, freeze,
                               read_json, read_response, response_dir, sha, write_json)
from llm_authoring.workspace import begin, choose_domain, choose_type, create_workspace
from llm_authoring.manual import (PLACEHOLDER, import_model, manual_status, prepare_model,
                                 validate_manual_evidence)
from llm_authoring.authoring import (check_seed, check_three, evaluation_template,
                                    self_review_template)
from llm_authoring.ranking import export_complete, ranking_template
from test_core import question
from test_arena_ranking import fill_five


class ManualTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / 'workspace'
        create_workspace(self.workspace)
        self.root = self.workspace / 'task'
        task=json.loads((self.root/'TASK.json').read_text());task.pop('platform_checks_required',None)
        (self.root/'TASK.json').write_text(json.dumps(task))
        # Preserve the v3 request format as a backwards-compatibility fixture.
        request=json.loads((self.root/'REQUEST.json').read_text());request.pop('selection_schema',None)
        (self.root/'REQUEST.json').write_text(json.dumps(request))
        choose_domain(self.root, '计算机科学')
        choose_type(self.root, '分析决策类')
        self.q = question(); self.q['task_id'] = 'question-001'
        freeze(self.root, self.q)
        (self.root / 'drafts/sources.md').write_text('合成测试的来源说明；不代表真实专业题目。')
    def tearDown(self): self.temp.cleanup()
    def fill(self, role, text='# 合成回复\n\n先核对验收依据；依据约束实现。\n'):
        path = Path(prepare_model(self.root, role)['input_file'])
        path.write_bytes(text.encode('utf-8'))
        return path
    def seed(self, met=False):
        self.fill('seed'); import_model(self.root, 'seed')
        ev = evaluation_template(self.root, ('seed',)); ev['reviewer'] = 'synthetic-test'
        for j in ev['models']['seed']['points'].values():
            j.update(met=met, reason='合成结构测试判断，仅验证流程约束。', quotes=['先核对验收依据'] if met else [])
        write_json(self.root / 'evaluations/seed-r0001.json', ev)
        return ev
    def three(self):
        self.seed()
        for role in ('gpt', 'claude'):
            self.fill(role); import_model(self.root, role)
        ev = evaluation_template(self.root); ev['reviewer'] = 'synthetic-test'
        for role, record in ev['models'].items():
            for j in record['points'].values():
                j.update(met=role != 'seed', reason='仅为合成流程判断，不代表专业评测结论。' * 8,
                         quotes=['先核对验收依据'] if role != 'seed' else [])
        return ev
    def test_new_workspace_needs_no_provider_file_or_credentials(self):
        self.assertTrue(begin(self.root, self.workspace)['ready'])
        self.assertFalse((self.workspace / 'local/providers.json').exists())
        self.assertEqual(read_json(self.root / 'TASK.json')['response_mode'], 'official_manual')
    def test_only_seed_file_is_created_before_screen(self):
        slot = prepare_model(self.root, 'seed')
        directory = Path(slot['input_file']).parent
        self.assertEqual(Path(slot['input_file']).read_text(), PLACEHOLDER)
        for role in ('gpt', 'claude'):
            with self.assertRaisesRegex(Error, '先导入 Seed'): prepare_model(self.root, role)
            with self.assertRaises(Error): import_model(self.root, role)
            self.assertFalse((directory / (role + '-request.json')).exists())
        self.assertEqual(manual_status(self.root)['stage'], 'awaiting_seed_markdown')
    def test_empty_placeholder_or_unclosed_markdown_cannot_be_imported(self):
        slot = Path(prepare_model(self.root, 'seed')['input_file'])
        for text in (PLACEHOLDER, ' ', '```py\ntruncated\n', '```md\n# wrapped\n```\n'):
            slot.write_text(text)
            with self.assertRaises(Error): import_model(self.root, 'seed')
            self.assertFalse(response_dir(self.root, 'seed').exists())
    def test_seed_true_unknown_and_stale_screen_block_both_prepare_and_import(self):
        ev = self.seed(True)
        for value in (True, None, False):
            broken = copy.deepcopy(ev)
            for j in broken['models']['seed']['points'].values():
                j['met'] = value
            if value is False: broken['question_sha256'] = 'stale'
            write_json(self.root / 'evaluations/seed-r0001.json', broken)
            for role in ('gpt', 'claude'):
                with self.assertRaises(Error): prepare_model(self.root, role)
                with self.assertRaises(Error): import_model(self.root, role)
        self.assertFalse((self.root / 'model-input/r0001/GPT-5.6 sol.md').exists())
    def test_negative_screen_opens_followups_but_import_rechecks_gate(self):
        ev = self.seed()
        for role in ('gpt', 'claude'): self.fill(role)
        for j in ev['models']['seed']['points'].values(): j.update(met=True, quotes=['先核对验收依据'])
        write_json(self.root / 'evaluations/seed-r0001.json', ev)
        for role in ('gpt', 'claude'):
            with self.assertRaisesRegex(Error, 'Seed 已达成'): import_model(self.root, role)
            self.assertFalse(response_dir(self.root, role).exists())
    def test_filled_files_are_not_overwritten_and_import_is_idempotent(self):
        slot = self.fill('seed'); before = slot.read_bytes()
        prepare_model(self.root, 'seed'); self.assertEqual(slot.read_bytes(), before)
        import_model(self.root, 'seed')
        saved = read_response(self.root, 'seed'); digest = sha(saved['directory'] / 'metadata.json')
        import_model(self.root, 'seed'); self.assertEqual(sha(saved['directory'] / 'metadata.json'), digest)
        slot.write_text('不同的模型回答。')
        with self.assertRaisesRegex(Error, '不同'): import_model(self.root, 'seed')
        self.assertEqual((saved['directory'] / 'reply.md').read_bytes(), before)
    def test_original_bytes_preserved_with_crlf_unicode_and_tables(self):
        text = '# 合成答复\r\n\r\n| 变量 | 说明 |\r\n|---|---|\r\n| 中文 | 保留 |\r\n'
        slot = self.fill('seed', text); import_model(self.root, 'seed')
        item = validate_manual_evidence(self.root, 'seed')
        self.assertEqual((item['directory'] / 'reply.md').read_bytes(), slot.read_bytes())
        self.assertEqual(item['text'], text)
        self.assertEqual((item['directory'] / 'model-input.md').read_bytes(), slot.read_bytes())
    def test_changed_raw_original_and_changed_binding_are_rejected(self):
        self.seed(); item = read_response(self.root, 'seed')
        raw = item['directory'] / 'model-input.md'; old = raw.read_bytes(); raw.write_bytes(b'changed')
        with self.assertRaises(Error): check_seed(self.root, read_json(self.root / 'evaluations/seed-r0001.json'))
        raw.write_bytes(old)
        m = item['meta']; m['manual_request']['role'] = 'gpt'; write_json(item['directory'] / 'metadata.json', m)
        with self.assertRaisesRegex(Error, '绑定'): validate_manual_evidence(self.root, 'seed')
    def test_input_and_prompt_binding_tamper_or_symlinks_are_rejected(self):
        slot = Path(prepare_model(self.root, 'seed')['input_file'])
        prompt = slot.parent / 'prompt.md'; prompt.write_text('changed')
        with self.assertRaisesRegex(Error, '题面文件'): prepare_model(self.root, 'seed')
        slot.write_text('完整的合成回复。')
        with self.assertRaisesRegex(Error, '题面文件'): import_model(self.root, 'seed')
        self.assertFalse(response_dir(self.root, 'seed').exists())
        prompt.unlink(); prompt.symlink_to(self.root / 'drafts/sources.md')
        with self.assertRaisesRegex(Error, '题面文件'): import_model(self.root, 'seed')
        prompt.unlink(); prepare_model(self.root, 'seed')
        self.fill_manifest = slot.parent / 'seed-request.json'
        request = read_json(self.fill_manifest); request['prompt'] = 'changed'; write_json(self.fill_manifest, request)
        slot.write_text('完整的合成回复。')
        with self.assertRaisesRegex(Error, '绑定'): import_model(self.root, 'seed')
        slot.unlink(); slot.symlink_to(self.root / 'drafts/sources.md')
        with self.assertRaises(Error): prepare_model(self.root, 'seed')
    def test_insight_change_reuses_originals_but_requires_new_judgments(self):
        ev = self.three(); before = {role: sha(read_response(self.root, role)['directory'] / 'reply.md') for role in ROLES}
        q = copy.deepcopy(self.q); q['insight']['conclusion'] += '修订'; freeze(self.root, q)
        with self.assertRaisesRegex(Error, '完整冻结版本'): check_three(self.root, ev)
        updated = evaluation_template(self.root); updated['reviewer'] = ev['reviewer']; updated['models'] = copy.deepcopy(ev['models'])
        self.assertTrue(check_three(self.root, updated)['three_model_gate'])
        self.assertEqual(before, {role: sha(read_response(self.root, role)['directory'] / 'reply.md') for role in ROLES})
    def test_new_prompt_requires_new_seed_input_and_old_screen_cannot_unlock_followups(self):
        self.seed(); q = copy.deepcopy(self.q); q['prompt'] += '请说明。'; freeze(self.root, q)
        slot = Path(prepare_model(self.root, 'seed')['input_file'])
        self.assertIn('r0002', str(slot))
        with self.assertRaises(Error): prepare_model(self.root, 'gpt', self.root / 'evaluations/seed-r0001.json')
        self.assertFalse(response_dir(self.root, 'seed').exists())
    def test_full_flow_exports_six_md_with_no_screenshots_or_api_claim(self):
        three = self.three(); self.assertTrue(check_three(self.root, three)['three_model_gate'])
        five = fill_five(self.root, three)
        review = self_review_template(self.root); review['reviewer'] = 'synthetic-self-review'
        for j in review['checks'].values(): j.update(passed=True, reason='合成数据仅核对流程结构。')
        output = self.root / 'delivery/v001'
        result = export_complete(self.root, five, review, ranking_template(self.root, five), output)
        self.assertEqual(result['models'], 5)
        self.assertFalse((output / 'screenshots').exists())
        self.assertFalse(list(output.rglob('*.png')) + list(output.rglob('*.zip')))
        fields = read_json(output / 'fields.json'); self.assertEqual(fields['supporting_points'], '无')
        self.assertEqual(len(list((output / 'models').glob('*.md'))), 5)
        for role in ALL_ROLES:
            self.assertEqual((output / fields['models'][role]['reply_file']).read_bytes(),
                             (read_response(self.root, role)['directory'] / 'reply.md').read_bytes())
        main = (output / '提交信息.md').read_text()
        self.assertNotIn('# 合成回复', main); self.assertNotIn('API原文', main)
        self.assertNotRegex(main, r'模型[一二三四五1-5]')
        self.assertIn('官方网页截图由用户', main)
        for name, digest in read_json(output / 'manifest.json')['files'].items(): self.assertEqual(sha(output / name), digest)
        with self.assertRaises(Error): export_complete(self.root, five, review, ranking_template(self.root, five), output)
    def test_cli_manual_commands_work_without_configuration_or_network(self):
        from llm_authoring.cli import main
        args = ['--workspace', str(self.workspace), '--task', str(self.root)]
        with patch('llm_authoring.cli.collect') as collect, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(main(args + ['model-prepare', 'seed']), 0)
            self.fill('seed'); self.assertEqual(main(args + ['model-import', 'seed']), 0)
            self.assertEqual(main(args + ['model-prepare', 'gpt']), 2)
            collect.assert_not_called()
