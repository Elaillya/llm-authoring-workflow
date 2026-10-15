"""Synthetic prompt equality, plain-field export and flexible Insight regression."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from llm_authoring.core import Error,active_question,freeze,read_json,read_response,write_json
from llm_authoring.manual import prepare_model,import_model
from llm_authoring.arena import prepare_arena,import_arena
from llm_authoring.authoring import self_review_template
from llm_authoring.ranking import export_complete,ranking_template,validate_ranking
import test_manual as manual
import test_arena_ranking as arena
import test_platform_checks as platform
import test_diversity as diversity


class PlainContentTests(unittest.TestCase):
    setUp=manual.ManualTests.setUp
    tearDown=manual.ManualTests.tearDown
    fill=manual.ManualTests.fill
    three=manual.ManualTests.three

    def seed(self,met=False):
        from llm_authoring.authoring import evaluation_template
        self.fill('seed');import_model(self.root,'seed')
        ev=evaluation_template(self.root,('seed',));ev['reviewer']='synthetic-test'
        for item in ev['models']['seed']['points'].values():
            item.update(met=met,reason='合成结构判断。',quotes=['先核对验收依据'] if met else [])
        write_json(self.root/'evaluations'/('seed-'+active_question(self.root)['revision']+'.json'),ev)
        return ev

    def test_all_new_model_prompts_equal_frozen_prompt_bytes(self):
        three=self.three()
        expected=self.q['prompt'].encode()
        directory=self.root/'model-input/r0001'
        self.assertEqual((directory/'prompt.md').read_bytes(),expected)
        for role in ('seed','gpt','claude'):
            request=read_json(directory/(role+'-request.json'))
            self.assertNotIn('format_instruction',request)
            self.assertEqual(request['prompt_policy'],'prompt_only')
        entry=prepare_arena(self.root,three)
        self.assertEqual(Path(entry['prompt_file']).read_bytes(),expected)

    def test_arena_prompt_tamper_blocks_prepare_and_import(self):
        three=self.three();arena.fill_slots(self.root,three)
        prompt=self.root/'arena-input/r0001/arena-prompt.md';prompt.write_text(self.q['prompt']+'\n')
        with self.assertRaisesRegex(Error,'题面'):prepare_arena(self.root,three)
        with self.assertRaisesRegex(Error,'题面'):import_arena(self.root,three)

    def test_prompt_line_endings_are_preserved_and_checked_as_bytes(self):
        self.q['prompt']='这道合成题需要核对什么？\r\n请说明理由。';freeze(self.root,self.q)
        prompt=Path(prepare_model(self.root,'seed')['prompt_file'])
        self.assertEqual(prompt.read_bytes(),self.q['prompt'].encode())
        prompt.write_bytes(self.q['prompt'].replace('\r\n','\n').encode())
        with self.assertRaisesRegex(Error,'题面'):prepare_model(self.root,'seed')

    def test_old_insight_review_key_is_accepted_without_rewriting(self):
        from llm_authoring.authoring import validate_self_review
        review=self_review_template(self.root);review['reviewer']='synthetic-test'
        for item in review['checks'].values():item.update(passed=True,reason='合成自查。')
        review['checks']['insight_mechanism_priority_conclusion']=review['checks'].pop('insight_key_reasoning_and_conclusion')
        before=copy.deepcopy(review);validate_self_review(self.root,review)
        self.assertEqual(review,before)

    def test_legacy_manual_request_and_prompt_still_import_unchanged(self):
        slot=Path(prepare_model(self.root,'seed')['input_file']);manifest=slot.parent/'seed-request.json'
        request=read_json(manifest);request.pop('prompt_policy',None)
        request['format_instruction']='请使用 Markdown 格式回复，不要用最外层代码块包裹全文。'
        write_json(manifest,request)
        prompt=slot.parent/'prompt.md';prompt.write_text(request['prompt']+'\n\n'+request['format_instruction']+'\n')
        before=prompt.read_bytes();slot.write_text('完整的旧版合成原回复。')
        import_model(self.root,'seed')
        self.assertEqual(prompt.read_bytes(),before)
        self.assertEqual(read_response(self.root,'seed')['meta']['manual_request'],request)

    def test_legacy_arena_prompt_remains_readable(self):
        three=self.three();arena.fill_slots(self.root,three)
        directory=self.root/'arena-input/r0001';manifest=directory/'request.json'
        request=read_json(manifest);request.pop('prompt_policy',None);write_json(manifest,request)
        prompt=directory/'arena-prompt.md'
        prompt.write_text(self.q['prompt']+'\n\n请使用 Markdown 格式回复，不要用最外层代码块包裹全文。\n')
        before=prompt.read_bytes();prepare_arena(self.root,three);import_arena(self.root,three)
        self.assertEqual(prompt.read_bytes(),before)

    def test_official_complete_fenced_original_is_not_rewritten(self):
        text='```markdown\n# 官方原回答\n\n完整回答。\n```\n'
        slot=self.fill('seed',text);import_model(self.root,'seed')
        self.assertEqual((read_response(self.root,'seed')['directory']/'reply.md').read_bytes(),slot.read_bytes())

    def test_legacy_seed_followup_gets_separate_exact_prompt(self):
        self.test_legacy_manual_request_and_prompt_still_import_unchanged()
        from llm_authoring.authoring import evaluation_template
        ev=evaluation_template(self.root,('seed',));ev['reviewer']='synthetic-test'
        for item in ev['models']['seed']['points'].values():item.update(met=False,reason='缺少合成事实。',quotes=[])
        write_json(self.root/'evaluations/seed-r0001.json',ev)
        old=self.root/'model-input/r0001/prompt.md';before=old.read_bytes()
        slot=prepare_model(self.root,'gpt')
        self.assertEqual(Path(slot['prompt_file']).name,'prompt-only.md')
        self.assertEqual(Path(slot['prompt_file']).read_bytes(),self.q['prompt'].encode())
        self.assertEqual(old.read_bytes(),before)
        self.assertIn('新旧合同',slot['capture_contract_notice'])
        for role in ('gpt','claude'):
            self.fill(role);import_model(self.root,role)
        three=evaluation_template(self.root);three['reviewer']='synthetic-test'
        for role,record in three['models'].items():
            for item in record['points'].values():item.update(met=role!='seed',reason='合成判断。',quotes=['先核对验收依据'] if role!='seed' else [])
        from llm_authoring.authoring import check_three
        with self.assertRaisesRegex(Error,'新旧合同'):check_three(self.root,three)

    def test_plain_insight_exports_plain_metadata_and_unchanged_five_replies(self):
        self.q['insight']='验收依据决定实现范围。先确认目标，才能判断程序是否解决实际需求。计算2*3*4=24；入口名为__main__；指针int *p。'
        self.q['points'][0]['criterion']='判断验收依据是否约束实现。保留__init__、2*3*4及int *p。'
        freeze(self.root,self.q)
        three=self.three();five=arena.fill_five(self.root,three)
        review=self_review_template(self.root);review['reviewer']='synthetic-test'
        for item in review['checks'].values():item.update(passed=True,reason='合成结构自查。')
        ranking=ranking_template(self.root,five);ranking['summary']='考点达成决定次序，同分并列。'
        output=self.root/'delivery/plain';export_complete(self.root,five,review,ranking,output)
        text=(output/'提交信息.md').read_text()
        self.assertNotRegex(text,r'(?m)^\s*(?:#{1,6}\s|[-*+]\s|```|>)')
        self.assertNotIn('**',text);self.assertNotIn('`验收依据`',text)
        self.assertIn('验收依据决定实现范围',text)
        for literal in ('2*3*4=24','__main__','__init__','int *p'):self.assertIn(literal,text)
        self.assertIn('决定性核心考点的达成性排序说明',text)
        fields=read_json(output/'fields.json')
        for role in fields['models']:
            self.assertEqual((output/fields['models'][role]['reply_file']).read_bytes(),
                             (read_response(self.root,role)['directory']/'reply.md').read_bytes())

    def test_concise_ranking_keeps_required_five_model_coverage(self):
        five=arena.fill_five(self.root,self.three());ranking=ranking_template(self.root,five)
        ranking['summary']='按决定性达成及考点满足数排序，同分并列。'
        ranking['models']={role:'D1'+('未满足：缺少该判断。' if role=='seed' else '满足：明确给出了该判断。') for role in five['models']}
        self.assertTrue(validate_ranking(self.root,five,ranking)['three_model_gate'])
        ranking['models']['gpt']=''
        with self.assertRaisesRegex(Error,'备注'):validate_ranking(self.root,five,ranking)


class PlainPlatformTests(unittest.TestCase):
    setUp=platform.PlatformTests.setUp
    tearDown=platform.PlatformTests.tearDown
    candidate=platform.PlatformTests.candidate
    fill=platform.PlatformTests.fill
    seed=platform.PlatformTests.seed
    three=platform.PlatformTests.three
    run_check=platform.PlatformTests.run_check
    frozen=platform.PlatformTests.frozen

    def test_plain_insight_checks_memory_and_postpass_polish(self):
        from llm_authoring import platform_checks as qa,platform_polish as polish
        from llm_authoring.memory import context
        self.q['insight']='验收依据限定实际实现范围，先确定可观察目标，再核对实现是否对应目标。'
        self.q['text_format']='plain'
        value,send=self.run_check('question',q=self.q)
        self.assertEqual(value['state'],'passed')
        self.assertEqual(send.call_args.args[1]['params']['出题说明'],self.q['insight'])
        diversity.accept(self.root,self.q);freeze(self.root,self.q)
        three=self.three()
        with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:platform.response(
                'criteria' if p['plan_id']=='2' else 'attainment',details='检查通过，建议澄清说明表达。')) as send:
            qa.run_models(self.root,three)
        for call in send.call_args_list:
            self.assertFalse(call.args[1]['params']['决定性核心考点'].startswith('- '))
        self.assertIn('验收依据',context(self.b,self.ws)['topic_index'][0]['mechanism'])
        prepare_arena(self.root,three);decision=polish.template(self.root,three)
        decision.update(reviewer='synthetic-test',arena_notice='已发送 arena-prompt.md、model-4.md、model-5.md。')
        for item in decision['reviews'].values():item.update(passed=True,reason='仅澄清原有含义。')
        decision['changes']=[{'field':'insight','before':self.q['insight'],'after':self.q['insight']+'以上为同一判断主线。',
            'stage':'criteria','feedback_quote':'建议澄清说明表达','reason':'仅澄清原有说明，判断保持。'}]
        with patch('llm_authoring.platform_client.call') as send:
            polish.apply(self.root,three,decision);send.assert_not_called()
        five=arena.fill_five(self.root,three)
        review=self_review_template(self.root);review['reviewer']='synthetic-test'
        for item in review['checks'].values():item.update(passed=True,reason='合成流程检查。')
        output=self.root/'delivery/plain';export_complete(self.root,five,review,ranking_template(self.root,five),output)
        self.assertIn('以上为同一判断主线', (output/'提交信息.md').read_text())

    def test_insight_shapes_are_compared_by_local_memory(self):
        from llm_authoring.quality import candidate_check
        self.run_check('question',q=self.q);diversity.accept(self.root,self.q);freeze(self.root,self.q)
        other=copy.deepcopy(self.q);other['task_id']=read_json(self.b/'TASK.json')['task_id']
        other['insight']='\n'.join(self.q['insight'][key] for key in ('mechanism','priority','conclusion'))
        (self.b/'drafts/sources.md').write_text('合成专业来源。')
        report=candidate_check(self.b,other)
        self.assertTrue(any('insight' in item['fields'] for item in report['hard_duplicates']))
