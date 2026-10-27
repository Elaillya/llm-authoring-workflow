"""Automation branch tasks run without local platform-check gates by configuration."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile, unittest

import test_diversity as diversity
from llm_authoring import platform_checks as qa
from llm_authoring.arena import prepare_arena
from llm_authoring.authoring import check_three, evaluation_template
from llm_authoring.cli import main
from llm_authoring.core import ARENA_ROLES, Error, active_question, freeze, read_json, write_json
from llm_authoring.manual import import_model, prepare_model
from llm_authoring.selection import choose_subdirection
from llm_authoring.workspace import choose_domain, choose_type, create_task


class AutomationBranchTests(unittest.TestCase):
    candidate = diversity.DiversityTests.candidate

    def setUp(self):
        diversity.DiversityTests.setUp(self)
        self.root = Path(create_task(self.ws, 'auto-1', platform_checks=False)['task'])
        choose_domain(self.root, '计算机科学')
        choose_subdirection(self.root, 'cs_courses')
        choose_type(self.root, '分析决策类')
        (self.root / 'drafts/sources.md').write_text('合成测试的专业依据说明，未开展真实专业实验。')
        self.q = self.candidate(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def fill(self, role, text='# 合成回复\n\n先核对验收依据；依据约束实现。\n'):
        path = Path(prepare_model(self.root, role)['input_file'])
        path.write_bytes(text.encode('utf-8'))
        return path

    def three_gate_evaluation(self):
        self.fill('seed'); import_model(self.root, 'seed')
        seed_ev = evaluation_template(self.root, ('seed',)); seed_ev['reviewer'] = 'synthetic-test'
        for j in seed_ev['models']['seed']['points'].values():
            j.update(met=False, reason='合成结构测试判断，仅验证流程约束。', quotes=[])
        write_json(self.root / 'evaluations/seed-r0001.json', seed_ev)
        for role in ('gpt', 'claude'):
            self.fill(role); import_model(self.root, role)
        ev = evaluation_template(self.root); ev['reviewer'] = 'synthetic-test'
        for role, record in ev['models'].items():
            for j in record['points'].values():
                j.update(met=role != 'seed', reason='仅为合成流程判断，不代表专业评测结论。' * 8,
                         quotes=['先核对验收依据'] if role != 'seed' else [])
        return ev

    def test_flag_writes_explicit_false_and_default_stays_true(self):
        self.assertIs(read_json(self.root / 'TASK.json')['platform_checks_required'], False)
        default = Path(create_task(self.ws, 'manual-1')['task'])
        self.assertIs(read_json(default / 'TASK.json')['platform_checks_required'], True)

    def test_cli_flag_creates_gate_free_task(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(main(['--workspace', str(self.ws.resolve()), 'new', 'auto-2', '--no-platform-checks']), 0)
            self.assertEqual(main(['--workspace', str(self.ws.resolve()), 'new', 'auto-3']), 0)
        self.assertIs(read_json(self.ws / 'question-auto-2/TASK.json')['platform_checks_required'], False)
        self.assertIs(read_json(self.ws / 'question-auto-3/TASK.json')['platform_checks_required'], True)

    def test_status_reports_legacy_contract_without_platform_stages(self):
        self.assertFalse(qa.required(self.root))
        self.assertEqual(qa.status(self.root), {'required': False, 'stage': 'legacy_contract'})

    def test_freeze_imports_and_arena_prepare_pass_without_any_check_records(self):
        diversity.accept(self.root, self.q)
        freeze(self.root, self.q)
        ev = self.three_gate_evaluation()
        self.assertTrue(check_three(self.root, ev)['three_model_gate'])
        result = prepare_arena(self.root, ev)
        directory = self.root / 'arena-input/r0001'
        self.assertTrue(directory.is_dir())
        self.assertTrue((directory / 'arena-prompt.md').is_file())
        self.assertEqual(set(result['input_files']), set(ARENA_ROLES))

    def test_required_task_freeze_still_demands_question_check(self):
        manual = Path(create_task(self.ws, 'manual-2')['task'])
        choose_domain(manual, '计算机科学')
        choose_subdirection(manual, 'cs_courses')
        choose_type(manual, '分析决策类')
        q = self.candidate(manual)
        (manual / 'drafts/sources.md').write_text('合成测试的专业依据说明，未开展真实专业实验。')
        diversity.accept(manual, q)
        with self.assertRaisesRegex(Error, 'qa-run question'):
            freeze(manual, q)

    def test_automation_task_switches_subdirection_and_type_after_freeze(self):
        diversity.accept(self.root, self.q)
        freeze(self.root, self.q)
        frozen = (self.root / 'revisions/r0001/question.json').read_bytes()
        choose_subdirection(self.root, 'cs_research')
        choose_type(self.root, 'How-to类')
        request = read_json(self.root / 'REQUEST.json')
        self.assertEqual(request['subdirection'], 'cs_research')
        self.assertEqual(request['subdirection_confirmed'], True)
        self.assertEqual(request['question_type'], 'How-to类')
        with self.assertRaisesRegex(Error, '新建题目'):
            choose_domain(self.root, '商科')
        q2 = self.candidate(self.root, variant=1)
        q2.update(subdirection='cs_research', question_type='How-to类')
        (self.root / 'drafts/sources.md').write_text('换向后的合成测试专业依据说明，未开展真实专业实验。')
        diversity.accept(self.root, q2)
        freeze(self.root, q2)
        self.assertEqual(read_json(self.root / 'CURRENT.json')['revision'], 'r0002')
        self.assertEqual(active_question(self.root)['question']['subdirection'], 'cs_research')
        self.assertEqual(
            frozen, (self.root / 'revisions/r0001/question.json').read_bytes(),
            '换向不得改写已冻结候选的证据')

    def test_legacy_task_without_flag_keeps_frozen_selection_lock(self):
        legacy = Path(create_task(self.ws, 'legacy-1')['task'])
        task = read_json(legacy / 'TASK.json'); task.pop('platform_checks_required'); write_json(legacy / 'TASK.json', task)
        choose_domain(legacy, '计算机科学')
        choose_subdirection(legacy, 'cs_courses')
        choose_type(legacy, '分析决策类')
        q = self.candidate(legacy)
        (legacy / 'drafts/sources.md').write_text('合成测试的专业依据说明，未开展真实专业实验。')
        diversity.accept(legacy, q)
        freeze(legacy, q)
        with self.assertRaisesRegex(Error, '不能更换子方向'):
            choose_subdirection(legacy, 'cs_research')
        with self.assertRaisesRegex(Error, '改题型'):
            choose_type(legacy, 'How-to类')


if __name__ == '__main__':
    unittest.main()
