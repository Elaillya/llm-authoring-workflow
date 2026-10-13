"""Synthetic Arena submissions; these tests never access Arena or model APIs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from llm_authoring.core import (ALL_ROLES, ARENA_ROLES, Error, active_question,
                               freeze, read_response, response_dir, sha)
from llm_authoring.arena import prepare_arena, import_arena
from llm_authoring.ranking import (check_five, export_complete, five_evaluation_template,
                                   ranking_template, validate_ranking, ranking_notes)
from llm_authoring.delivery import named_text
from test_core import prepared, populate, question
from test_export import ExportTests


def fill_slots(root, evaluation, names=('fixture-model-4', 'fixture-model-5')):
    paths = prepare_arena(root, evaluation)['input_files']
    for role, name in zip(ARENA_ROLES, names):
        Path(paths[role]).write_text(f'---\nmodel_name: {name}\n---\n# 合成测试回复\n\n先核对验收依据；依据约束实现。\n')
    return paths


def fill_five(root, three, names=('fixture-model-4', 'fixture-model-5')):
    fill_slots(root, three, names)
    import_arena(root)
    evaluation = five_evaluation_template(root, three)
    for role, record in evaluation['models'].items():
        for judgment in record['points'].values():
            if judgment['met'] is None:
                judgment.update({'met': True, 'reason': '合成测试明确说明依据约束实现，满足本测试标准；不代表真实专业评测。' * 6,
                                 'quotes': ['先核对验收依据']})
    return evaluation


def rebind_three(root, three):
    from llm_authoring.authoring import evaluation_template
    result = evaluation_template(root)
    result['reviewer'] = three['reviewer']
    for role in result['models']:
        result['models'][role]['points'] = copy.deepcopy(three['models'][role]['points'])
    return result


class ArenaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        prepared(self.root)
        self.three = populate(self.root)
    def tearDown(self): self.tmp.cleanup()
    def test_created_slots_are_idempotent_and_do_not_require_screenshots(self):
        paths = fill_slots(self.root, self.three)
        before = {role: Path(path).read_bytes() for role, path in paths.items()}
        self.assertFalse(prepare_arena(self.root, self.three)['screenshots_required'])
        self.assertEqual(before, {role: Path(path).read_bytes() for role, path in paths.items()})
        import_arena(self.root)
        for role in ARENA_ROLES:
            self.assertFalse(list(response_dir(self.root, role).glob('*.png')))
            self.assertIn('先核对验收依据', read_response(self.root, role)['text'])
        self.assertEqual(import_arena(self.root)['stage'], 'five_model_evaluation')
    def test_empty_second_slot_prevents_any_import(self):
        paths = prepare_arena(self.root, self.three)['input_files']
        Path(paths['arena_1']).write_text('---\nmodel_name: fixture-4\n---\n完整测试回复\n')
        with self.assertRaisesRegex(Error, '填写'): import_arena(self.root)
        self.assertFalse(response_dir(self.root, 'arena_1').exists())
    def test_excluded_or_duplicate_names_are_rejected_before_import(self):
        for names in [('gpt-new', 'fixture-5'), ('Claude-other', 'fixture-5'),
                      ('doubao-seed-2-1-turbo', 'fixture-5'), ('fixture-A', 'FIXTURE_A')]:
            fill_slots(self.root, self.three, names)
            with self.assertRaises(Error): import_arena(self.root)
            self.assertFalse(response_dir(self.root, 'arena_1').exists())
    def test_new_question_binding_rejects_old_slot_manifest(self):
        fill_slots(self.root, self.three)
        request = self.root / 'arena-input/r0001/request.json'
        value = json.loads(request.read_text()); value['question_sha256'] = 'stale'
        request.write_text(json.dumps(value))
        with self.assertRaisesRegex(Error, '绑定'): import_arena(self.root)
    def test_imported_original_is_never_overwritten(self):
        paths = fill_slots(self.root, self.three); import_arena(self.root)
        original = (response_dir(self.root, 'arena_1') / 'reply.md').read_bytes()
        Path(paths['arena_1']).write_text('---\nmodel_name: fixture-model-4\n---\n不同的回复\n')
        with self.assertRaisesRegex(Error, '已有'): import_arena(self.root)
        self.assertEqual((response_dir(self.root, 'arena_1') / 'reply.md').read_bytes(), original)
    def test_unclosed_markdown_and_modified_raw_are_rejected(self):
        paths = fill_slots(self.root, self.three)
        Path(paths['arena_2']).write_text('---\nmodel_name: fixture-model-5\n---\n```py\ntruncated\n')
        with self.assertRaisesRegex(Error, '未闭合'): import_arena(self.root)
        fill_slots(self.root, self.three); import_arena(self.root)
        (response_dir(self.root, 'arena_1') / 'arena-input.md').write_text('changed')
        with self.assertRaises(Error): read_response(self.root, 'arena_1')
    def test_three_model_gate_must_pass_before_preparing_slots(self):
        for judgment in self.three['models']['seed']['points'].values():
            judgment.update({'met': True, 'quotes': ['先核对验收依据']})
        with self.assertRaisesRegex(Error, '门槛'): prepare_arena(self.root, self.three)
    def test_first_three_decisive_judgments_are_copied_without_changing_original(self):
        original = copy.deepcopy(self.three)
        fill_slots(self.root, self.three); import_arena(self.root)
        five = five_evaluation_template(self.root, self.three)
        for role in ('seed', 'gpt', 'claude'):
            self.assertEqual(five['models'][role]['points'], self.three['models'][role]['points'])
        self.assertEqual(original, self.three)


class RankingTests(ArenaTests):
    def test_name_conversion_preserves_normal_chinese_narrative(self):
        names={role:read_response(self.root,role)['meta']['display_name'] for role in ('seed','gpt','claude')}
        names.update({'arena_1':'fixture-four','arena_2':'fixture-five'})
        narrative='五个模型一致遵循冻结标准。这个模型一般讨论恢复，模型一开始进行检查，模型二次推理。'
        self.assertEqual(named_text(narrative,names),narrative)
        self.assertEqual(named_text('模型一：未达成；模型2达成。',names),'Seed 2.1 Turbo：未达成；GPT-5.6 sol达成。')
    def test_ties_use_real_names_and_ranking_is_bound_to_evaluation(self):
        five = fill_five(self.root, self.three)
        result = check_five(self.root, five)
        self.assertEqual(result['order'], 'GPT-5.6 sol = Claude Opus 4.6 = fixture-model-4 = fixture-model-5 > Seed 2.1 Turbo')
        ranking = ranking_template(self.root, five)
        self.assertNotRegex(ranking_notes(ranking), r'模型[一二三四五1-5]')
        for name in result['models'].values():
            self.assertIn(name['name'], ranking_notes(ranking))
        validate_ranking(self.root, five, ranking)
        changed = copy.deepcopy(five); changed['models']['arena_1']['points']['D1']['reason'] += '修订说明'
        with self.assertRaisesRegex(Error, 'evaluation_sha256'): validate_ranking(self.root, changed, ranking)
        ranking['groups'] = [['gpt'], ['claude', 'arena_1', 'arena_2'], ['seed']]
        with self.assertRaisesRegex(Error, 'groups'): validate_ranking(self.root, five, ranking)
    def test_legacy_ordinal_order_is_accepted_but_rendered_with_names(self):
        five = fill_five(self.root, self.three)
        ranking = ranking_template(self.root, five)
        del ranking['display_names']
        ranking['order'] = '模型2 = 模型3 = 模型4 = 模型5 > 模型1'
        ranking['summary'] = '模型2、模型3、模型4和模型5全部达成；模型1未全部达成。'
        expected = check_five(self.root, five)
        self.assertEqual(validate_ranking(self.root, five, ranking)['order'], expected['order'])
        output = ranking_notes(ranking, {role: item['name'] for role, item in expected['models'].items()})
        self.assertNotRegex(output, r'模型[一二三四五1-5]')
        self.assertIn('Seed 2.1 Turbo未全部达成', output)
    def test_reason_requires_summary_all_five_models_and_500_characters(self):
        five = fill_five(self.root, self.three)
        ranking = ranking_template(self.root, five)
        ranking['summary'] = ''
        with self.assertRaisesRegex(Error, '总结'): validate_ranking(self.root, five, ranking)
        ranking['summary'] = '总结'; ranking['models'] = {role: '简短说明' for role in ALL_ROLES}
        with self.assertRaisesRegex(Error, '500'): validate_ranking(self.root, five, ranking)
    def test_all_decisive_has_priority_and_total_points_sort_within_tier(self):
        q = question()
        q['points'] += [{'id': f'N{i}', 'kind': 'supporting', 'criterion': '合成辅助标准'} for i in range(1, 4)]
        freeze(self.root, q)
        self.three = rebind_three(self.root, self.three)
        five = fill_five(self.root, self.three)
        for role in ALL_ROLES:
            for key, judgment in five['models'][role]['points'].items():
                judgment.update({'met': role == 'gpt' and key.startswith('D'), 'reason': '合成测试标准的具体解释。',
                                 'quotes': ['先核对验收依据'] if role == 'gpt' and key.startswith('D') else []})
        for key in ['N1', 'N2', 'N3']:
            five['models']['seed']['points'][key].update({'met': True, 'quotes': ['先核对验收依据']})
        five['models']['claude']['points']['D1'].update({'met': True, 'quotes': ['先核对验收依据']})
        result = check_five(self.root, five)
        self.assertEqual(result['groups'][0], ['gpt'])
        self.assertEqual(result['groups'][1], ['seed'])
        self.assertEqual(result['groups'][2], ['claude'])
        five['models']['arena_1']['points']['N1']['met'] = None
        with self.assertRaisesRegex(Error, '证据不足'): check_five(self.root, five)
    def test_supporting_judgments_cannot_be_omitted(self):
        q = question(); q['points'].append({'id': 'N1', 'kind': 'supporting', 'criterion': '合成辅助标准'})
        freeze(self.root, q); three = rebind_three(self.root, self.three)
        five = fill_five(self.root, three)
        del five['models']['gpt']['points']['N1']
        with self.assertRaisesRegex(Error, '全部指定'): check_five(self.root, five)


class CompleteExportTests(unittest.TestCase):
    setUp = ExportTests.setUp
    tearDown = ExportTests.tearDown
    def test_complete_export_has_five_originals_and_only_three_required_images(self):
        five = fill_five(self.root, self.ev)
        ranking = ranking_template(self.root, five)
        before = {role: sha(read_response(self.root, role)['directory'] / 'reply.md') for role in ALL_ROLES}
        output = self.root / 'delivery/v002'
        export_complete(self.root, five, self.review, ranking, output)
        fields = json.loads((output / 'fields.json').read_text())
        self.assertEqual(list(fields['models']), list(ALL_ROLES))
        self.assertEqual(fields['supporting_points'], '无')
        self.assertEqual(fields['ranking'], ranking['order'])
        self.assertEqual(len(list((output / 'screenshots').glob('*.png'))), 3)
        for role in ALL_ROLES:
            model_file = output / fields['models'][role]['reply_file']
            self.assertEqual(model_file.name, fields['models'][role]['display_name'] + '.md')
            self.assertEqual(sha(model_file), before[role])
            self.assertEqual(sha(read_response(self.root, role)['directory'] / 'reply.md'), before[role])
        metadata = (output / '提交信息.md').read_text()
        self.assertNotIn('### 模型回复', metadata)
        self.assertNotIn('# 合成测试回复', metadata)
        self.assertNotRegex(metadata, r'模型[一二三四五1-5]')
        self.assertEqual(len(list(output.rglob('*.md'))) - len(list((output/'evidence').rglob('*.md'))), 6)
        self.assertFalse((output/'出题提交.md').exists())
        self.assertFalse(list(output.rglob('*.zip')))
        self.assertTrue((output/'提交信息.md').exists())
        handoff = json.loads((output / 'handoff.json').read_text())
        self.assertEqual(handoff['kind'], 'llm_complete_submission')
        self.assertEqual(handoff['next_workflow'], 'platform_submission')
        for name, digest in json.loads((output / 'manifest.json').read_text())['files'].items():
            self.assertEqual(sha(output / name), digest)
        with self.assertRaisesRegex(Error, '拒绝覆盖'): export_complete(self.root, five, self.review, ranking, output)
    def test_missing_arena_does_not_create_a_final_submission(self):
        with self.assertRaises(Error): five_evaluation_template(self.root, self.ev)
        self.assertFalse((self.root / 'delivery/v002').exists())
    def test_model_filenames_are_safe_and_keep_original_unicode_markdown(self):
        five = fill_five(self.root, self.ev, names=('fixture/model:4', '中文-model-5'))
        output = self.root/'delivery/safe-names'
        export_complete(self.root, five, self.review, ranking_template(self.root,five), output)
        fields = json.loads((output/'fields.json').read_text())
        for role in ALL_ROLES:
            model = fields['models'][role]
            file = output/model['reply_file']
            self.assertEqual(file.parent,output/'models')
            self.assertNotRegex(file.name,r'[<>:"/\\|?*]')
            self.assertEqual(file.read_bytes(),(read_response(self.root,role)['directory']/'reply.md').read_bytes())
        self.assertIn('中文-model-5.md',[p.name for p in (output/'models').iterdir()])
        self.assertIn('fixture/model:4',(output/'提交信息.md').read_text())
