"""Postpass presentation changes never resend checks or replace frozen evidence."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import copy,json,unittest
from llm_authoring import platform_checks as qa,platform_polish as polish
from llm_authoring.arena import prepare_arena
from llm_authoring.authoring import self_review_template
from llm_authoring.core import Error,active_question,freeze,read_json,read_response,write_json
from llm_authoring.ranking import export_complete,ranking_template
import test_platform_checks as fixtures
import test_arena_ranking as arena_fixtures
import test_diversity as diversity


class PolishTests(unittest.TestCase):
    setUp=fixtures.PlatformTests.setUp
    tearDown=fixtures.PlatformTests.tearDown
    candidate=fixtures.PlatformTests.candidate
    fill=fixtures.PlatformTests.fill
    seed=fixtures.PlatformTests.seed
    three=fixtures.PlatformTests.three
    run_check=fixtures.PlatformTests.run_check
    frozen=fixtures.PlatformTests.frozen

    def ready(self):
        self.frozen();ev=self.three()
        with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:fixtures.response(
                'criteria' if p['plan_id']=='2' else 'attainment',details='检查通过。建议将说明表述得更清楚，保持原有标准。')):
            qa.run_models(self.root,ev)
        return ev

    def decision(self,ev):
        prepare_arena(self.root,ev);decision=polish.template(self.root,ev)
        decision.update(reviewer='synthetic-author',arena_notice='已向用户发送 arena-prompt.md、model-4.md 和 model-5.md 填写链接。')
        for item in decision['reviews'].values():item.update(passed=True,reason='合成验证：仅澄清说明句式，边界、引用和真假判断保持。')
        before=active_question(self.root)['question']['insight']['priority']
        decision['changes']=[{'field':'insight.priority','before':before,'after':before+'（澄清原有表述）',
            'stage':'criteria','feedback_quote':'建议将说明表述得更清楚','reason':'本测试只追加澄清标记，原含义保持。'}]
        return decision

    def test_all_passes_and_arena_files_and_actual_notification_required(self):
        ev=self.ready()
        with self.assertRaises(Error):polish.template(self.root,ev)
        decision=self.decision(ev);decision['arena_notice']=''
        with self.assertRaisesRegex(Error,'填写提示'):polish.apply(self.root,ev,decision)

    def test_polish_never_calls_the_service_and_keeps_frozen_and_prompt_bytes(self):
        ev=self.ready();decision=self.decision(ev)
        originals={str(p):p.read_bytes() for directory in ('revisions','responses','arena-input') for p in (self.root/directory).rglob('*') if p.is_file()}
        with patch('llm_authoring.platform_client.call') as send:
            result=polish.apply(self.root,ev,decision);qa.final_gate(self.root,ev)
            send.assert_not_called();self.assertEqual(result['platform_requests'],0)
        self.assertTrue(all(Path(name).read_bytes()==data for name,data in originals.items()))

    def test_prompt_verdict_citations_and_foreign_feedback_cannot_be_polished(self):
        ev=self.ready();original=self.decision(ev)
        for field in ('prompt','points.D1.kind','models.gpt.points.D1.met','reasons.arena_1.D1'):
            decision=copy.deepcopy(original);decision['changes'][0]['field']=field
            with self.assertRaises(Error):polish.apply(self.root,ev,decision)
        decision=copy.deepcopy(original);decision['changes'][0]['feedback_quote']='不在本次反馈中'
        with self.assertRaisesRegex(Error,'通过反馈'):polish.apply(self.root,ev,decision)
        decision=copy.deepcopy(original);decision['reviews']['rubric_meaning_unchanged']['passed']=False
        with self.assertRaises(Error):polish.apply(self.root,ev,decision)

    def test_disputed_return_is_not_treated_as_three_actual_passes(self):
        ev=self.ready();decision=self.decision(ev)
        self.run_check('criteria',ev=ev,decision='不通过',details='缺少必要约束。',refresh=True)
        d=qa.disagreement_template(self.root,'criteria',ev)
        d.update(reviewer='synthetic-author',reason='合成证据异议。',form_notes='不认同本次不通过，请复核题面约束。',
            evidence=[{'source':'feedback','quote':'缺少必要约束'},{'source':'input','field':'题目','quote':self.q['prompt']}])
        qa.disagree(self.root,d,ev)
        with self.assertRaisesRegex(Error,'实际通过'):polish.apply(self.root,ev,decision)

    def test_complete_delivery_uses_polished_text_and_only_six_markdown_files(self):
        ev=self.ready();decision=self.decision(ev);q=active_question(self.root)['question']
        decision['changes'].extend([
            {'field':'points.D1.criterion','before':q['points'][0]['criterion'],'after':q['points'][0]['criterion']+'（明确原有边界）',
             'stage':'criteria','feedback_quote':'建议将说明表述得更清楚','reason':'同一条件的说明性澄清。'},
            {'field':'reasons.gpt.D1','before':ev['models']['gpt']['points']['D1']['reason'],
             'after':ev['models']['gpt']['points']['D1']['reason']+'判定及所引原文保持。',
             'stage':'attainment','feedback_quote':'建议将说明表述得更清楚','reason':'只澄清既有判断依据。'}])
        original_ev=copy.deepcopy(ev);polish.apply(self.root,ev,decision)
        with patch('llm_authoring.platform_client.call') as send:
            five=arena_fixtures.fill_five(self.root,ev);review=self_review_template(self.root);review['reviewer']='synthetic-author'
            for item in review['checks'].values():item.update(passed=True,reason='合成完整流程验证。')
            output=self.root/'delivery/v001';export_complete(self.root,five,review,ranking_template(self.root,five),output)
            send.assert_not_called()
        text=(output/'提交信息.md').read_text();fields=read_json(output/'fields.json')
        for change in decision['changes']:self.assertIn(change['after'],text)
        self.assertIn('优化后未再次调用质检',text);self.assertEqual(ev,original_ev)
        self.assertEqual(read_json(output/'question.json')['question'],q)
        self.assertEqual(len(list(output.glob('*.md')))+len(list((output/'models').glob('*.md'))),6)
        for role,item in fields['models'].items():
            self.assertEqual((output/item['reply_file']).read_bytes(),(read_response(self.root,role)['directory']/'reply.md').read_bytes())
        self.assertTrue((output/'evidence/platform/postpass-polish.json').is_file())

    def test_changed_evaluation_cannot_reuse_old_polish(self):
        ev=self.ready();decision=self.decision(ev);polish.apply(self.root,ev,decision)
        ev['models']['gpt']['points']['D1']['reason']+='实质补充。'
        with self.assertRaises(Error):polish.validate(self.root,ev,decision)

    def test_question_disagreement_has_copiable_notes_and_never_forges_pass(self):
        self.run_check('question',q=self.q,decision='不通过',details='题目不可作答，但反馈没有指出实际缺失的条件。')
        d=qa.disagreement_template(self.root,'question',q=self.q)
        d.update(reviewer='synthetic-author',reason='合成测试的反馈没有定位差异；保留实际约束与专业依据，不能将此测试当真实专家结论。',
                 form_notes='不认同本次不通过结论，请对照已提供约束指出具体缺失条件。',
                 evidence=[{'source':'feedback','quote':'没有指出实际缺失的条件'},{'source':'input','field':'题目','quote':self.q['prompt']}])
        result=qa.disagree(self.root,d,q=self.q)
        self.assertIn('不认同',result['message']);self.assertIn(d['form_notes'],Path(result['notes_file']).read_text())
        self.assertEqual(qa.question_gate(self.root,self.q)['server_conclusion'],'不通过')
        diversity.accept(self.root,self.q);freeze(self.root,self.q)
        with self.assertRaises(Error):qa.disagreement_template(self.root,'question',q={**self.q,'prompt':self.q['prompt']+'新条件'})

    def test_cli_runs_pair_and_offline_polish_without_extra_requests(self):
        from llm_authoring.cli import main
        self.frozen();ev=self.three();ev_file=self.root/'evaluations/three.json';write_json(ev_file,ev)
        args=['--workspace',str(self.ws),'--task',str(self.root)];out=StringIO()
        with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:fixtures.response(
                'criteria' if p['plan_id']=='2' else 'attainment',details='检查通过。建议将说明表述得更清楚。')) as send,redirect_stdout(out):
            self.assertEqual(main(args+['qa-run','models','--evaluation',str(ev_file)]),0);self.assertEqual(send.call_count,2)
        decision=self.decision(ev);decision_file=self.root/'evaluations/polish.json';write_json(decision_file,decision)
        with patch('llm_authoring.platform_client.call') as send,redirect_stdout(out),redirect_stderr(StringIO()):
            self.assertEqual(main(args+['qa-polish',str(decision_file),'--evaluation',str(ev_file)]),0);send.assert_not_called()
        self.assertNotIn('TEST-ONLY-CREDENTIAL',out.getvalue())
