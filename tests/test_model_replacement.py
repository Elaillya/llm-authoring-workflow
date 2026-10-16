"""Explicitly authorized same-prompt replacement retains every old original."""
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
import copy,json,unittest
import test_platform_checks as fixture
from llm_authoring import replacement,lessons
from llm_authoring.core import Error,read_response,read_json,write_json,freeze
from llm_authoring.authoring import check_three,evaluation_template
from llm_authoring import platform_checks as qa
from test_diversity import accept
from llm_authoring.cli import main

class ReplacementTests(unittest.TestCase):
    candidate=fixture.PlatformTests.candidate
    setUp=fixture.PlatformTests.setUp
    tearDown=fixture.PlatformTests.tearDown
    fill=fixture.PlatformTests.fill
    seed=fixture.PlatformTests.seed
    three=fixture.PlatformTests.three
    frozen=fixture.PlatformTests.frozen
    run_check=fixture.PlatformTests.run_check
    def ready(self):
        self.frozen();self.ev=self.three()
        self.run_check('criteria',ev=self.ev,decision='不通过',details='D1的边界不清晰，需要按原题已给出的条件拆开判断。')
        eid=lessons.failure_context(self.root,self.ws)['pending_reviews'][0]['event_id']
        review=lessons.review_template(self.ws,eid)
        review.update(verdict='accepted',reviewer='synthetic-author',cause='当前考点边界表述不明确。',prevention='按题中事实拆开判定。',
                      applicability='仅这类边界未清楚的题。',evidence_quotes=['D1的边界不清晰'])
        lessons.review(self.ws,review);return eid
    def prepare(self,role='claude',**kw):
        return replacement.prepare(self.root,role,self.eid,authorization_note='用户在本对话明确同意重新提供Claude原文。',
                                   reason='按专业依据修正后需要对当前缺口获取新回复；保留同一prompt。',**kw)
    def test_missing_authorization_or_unreviewed_failure_cannot_prepare(self):
        self.eid=self.ready()
        with self.assertRaisesRegex(Error,'授权|同意'):replacement.prepare(self.root,'claude',self.eid,authorization_note='',reason='具体原因')
        self.assertFalse(list((self.root/'model-input').rglob('replacements')))
        decision=lessons.review_template(self.ws,self.eid);decision.update(verdict='unresolved',reviewer='test',cause='尚待核实')
        lessons.review(self.ws,decision)
        with self.assertRaisesRegex(Error,'认可'):self.prepare()
    def test_replacement_preserves_old_bytes_and_stales_old_evaluations(self):
        self.eid=self.ready();old=read_response(self.root,'claude');before={p.name:p.read_bytes() for p in old['directory'].iterdir()}
        protected={r:(read_response(self.root,r)['directory']/'reply.md').read_bytes() for r in ('seed','gpt')}
        plan=self.prepare();slot=Path(plan['input_file'])
        self.assertEqual(Path(plan['prompt_file']).read_bytes(),self.q['prompt'].encode())
        new=b'# New supplied answer\r\n\r\nA distinct full reply from the user.\r\n';slot.write_bytes(new)
        receipt=replacement.import_reply(self.root,'claude',plan['replacement_id'])
        self.assertEqual((read_response(self.root,'claude')['directory']/'reply.md').read_bytes(),new)
        archive=Path(receipt['archive'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in archive.iterdir()})
        for role,raw in protected.items():self.assertEqual((read_response(self.root,role)['directory']/'reply.md').read_bytes(),raw)
        with self.assertRaisesRegex(Error,'原文'):check_three(self.root,self.ev)
        self.assertTrue(replacement.import_reply(self.root,'claude',plan['replacement_id'])['already_imported'])
    def test_repaired_question_losing_gate_asks_before_replacement_without_quality_calls(self):
        self.eid=self.ready();ev=copy.deepcopy(self.ev)
        for role in ('gpt','claude'):
            for j in ev['models'][role]['points'].values():j.update(met=False,quotes=[])
        with patch('llm_authoring.platform_client.call') as call:
            with self.assertRaisesRegex(Error,'询问用户'):qa.run_models(self.root,ev)
            call.assert_not_called()
        self.assertEqual(qa.status(self.root,ev)['stage'],'criteria_repair_decision')
        self.prepare()
        with self.assertRaisesRegex(Error,'授权已有'):self.prepare()

    def test_prompt_change_cannot_reuse_replacement(self):
        self.eid=self.ready();plan=self.prepare()
        q=copy.deepcopy(self.q);q['prompt']='另一个不同题面应该怎样核实边界？'
        self.run_check('question',q=q);accept(self.root,q);freeze(self.root,q)
        with self.assertRaisesRegex(Error,'版本|题面'):replacement.import_reply(self.root,'claude',plan['replacement_id'])
    def test_placeholder_truncated_identical_or_changed_prompt_refused_before_mutation(self):
        self.eid=self.ready();plan=self.prepare();old=read_response(self.root,'claude')['text']
        for text in ('待粘贴完整 Markdown 回复\n','```py\ntruncated\n',old):
            Path(plan['input_file']).write_text(text)
            with self.assertRaises(Error):replacement.import_reply(self.root,'claude',plan['replacement_id'])
            self.assertEqual(read_response(self.root,'claude')['text'],old)
        Path(plan['input_file']).write_text('用户提供的新完整回复。')
        Path(plan['prompt_file']).write_text('被改过的题面')
        with self.assertRaises(Error):replacement.import_reply(self.root,'claude',plan['replacement_id'])
    def test_save_failure_restores_original_and_keeps_fill_in_file(self):
        self.eid=self.ready();plan=self.prepare();Path(plan['input_file']).write_text('用户提供的另一份完整原文。')
        old=read_response(self.root,'claude')['text']
        with patch('llm_authoring.replacement.save_response',side_effect=OSError('synthetic save failure')):
            with self.assertRaises(OSError):replacement.import_reply(self.root,'claude',plan['replacement_id'])
        self.assertEqual(read_response(self.root,'claude')['text'],old)
        self.assertTrue(Path(plan['input_file']).is_file())
        receipt=replacement.import_reply(self.root,'claude',plan['replacement_id'])
        self.assertEqual((Path(receipt['archive'])/'reply.md').read_text(),old)
        self.assertEqual(read_response(self.root,'claude')['text'],'用户提供的另一份完整原文。')
    def test_symlinked_archive_ancestor_rejected_before_moving_original(self):
        self.eid=self.ready();plan=self.prepare();Path(plan['input_file']).write_text('用户提供的新完整回复。')
        old=read_response(self.root,'claude');outside=self.root/'synthetic-outside';outside.mkdir()
        (old['directory'].parent/'.replacements').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(Error,'符号链接'):replacement.import_reply(self.root,'claude',plan['replacement_id'])
        self.assertEqual(read_response(self.root,'claude')['text'],old['text'])
        self.assertFalse(list(outside.iterdir()))
    def test_pending_new_reply_does_not_move_or_invalidate_current_original(self):
        self.eid=self.ready();old=read_response(self.root,'claude')['meta']
        plan=self.prepare();self.assertEqual(read_response(self.root,'claude')['meta'],old)
        self.assertTrue(check_three(self.root,self.ev)['three_model_gate'])
        output=StringIO()
        with redirect_stdout(output):self.assertEqual(main(['--task',str(self.root),'status']),0)
        status=json.loads(output.getvalue())
        self.assertEqual(status['stage'],'awaiting_replacement_markdown')
        self.assertEqual(status['model_input_files']['claude'],plan['input_file'])
        Path(plan['input_file']).write_text('用户提供的新回复，未假定一定命中。')
        replacement.import_reply(self.root,'claude',plan['replacement_id'])
        self.assertEqual(replacement.pending(self.root),[])
    def test_rubric_revision_reuses_originals_but_requires_uniform_reevaluation(self):
        self.eid=self.ready();before={r:read_response(self.root,r)['text'] for r in ('seed','gpt','claude')}
        q=copy.deepcopy(self.q);q['points'][0]['criterion']+='明确依据题面约束。'
        accept(self.root,q);freeze(self.root,q)
        for role,text in before.items():self.assertEqual(read_response(self.root,role)['text'],text)
        with self.assertRaisesRegex(Error,'考点'):check_three(self.root,self.ev)
        fresh=evaluation_template(self.root);fresh['reviewer']='test'
        for role,value in fresh['models'].items():value['points']=copy.deepcopy(self.ev['models'][role]['points'])
        self.assertTrue(check_three(self.root,fresh)['three_model_gate'])
        self.assertEqual(qa.status(self.root,fresh)['checks']['criteria']['state'],'pending')
