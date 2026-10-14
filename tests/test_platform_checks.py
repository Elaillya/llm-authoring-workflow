"""Synthetic gated checks and justified disagreement; no live platform calls."""
from pathlib import Path
from unittest.mock import patch
import copy,json,unittest
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Event
from llm_authoring import platform_checks as qa
from llm_authoring.platform_client import setup,KEYS
from llm_authoring.core import Error,freeze,read_json,write_json,read_response,sha
from llm_authoring.arena import prepare_arena,import_arena
from llm_authoring.authoring import self_review_template
from llm_authoring.ranking import export_complete,ranking_template
from test_platform_client import config
import test_diversity as diversity
import test_manual as manual
from test_arena_ranking import fill_five,fill_slots


def response(stage,conclusion='通过',details='合成测试检查通过，不代表真实专业判断。'):
    key,detail=KEYS[stage]
    return {'http_status':200,'response_text':json.dumps({'BaseResp':{'StatusCode':0},
            'response':json.dumps({key:conclusion,detail:details},ensure_ascii=False)},ensure_ascii=False),'truncated':False}


class PlatformTests(unittest.TestCase):
    candidate=diversity.DiversityTests.candidate
    tearDown=diversity.DiversityTests.tearDown
    fill=manual.ManualTests.fill
    seed=manual.ManualTests.seed
    three=manual.ManualTests.three
    def setUp(self):
        diversity.DiversityTests.setUp(self);self.root=self.a;self.workspace=self.ws;self.q=self.candidate(self.root)
        task=read_json(self.root/'TASK.json');task['platform_checks_required']=True;write_json(self.root/'TASK.json',task)
        self.files=setup(self.ws,config());Path(self.files['cookie_file']).write_text('sid=TEST-ONLY-CREDENTIAL')
    def run_check(self,stage,q=None,ev=None,decision='通过',details='合成测试检查通过，不代表真实专业判断。',**kwargs):
        with patch('llm_authoring.platform_client.call',return_value=response(stage,decision,details)) as send:
            value=qa.run(self.root,stage,q=q,evaluation=ev,**kwargs)
        return value,send
    def frozen(self):
        self.run_check('question',q=self.q);diversity.accept(self.root,self.q);freeze(self.root,self.q)
    def completed(self):
        self.frozen();ev=self.three();self.run_check('criteria',ev=ev);self.run_check('attainment',ev=ev);return ev
    def disputed(self):
        self.frozen();ev=self.three();self.run_check('criteria',ev=ev)
        self.run_check('attainment',ev=ev,decision='不通过',details='专家判断不一致，但Claude满足全部决定性考点。')
        decision=qa.disagreement_template(self.root,'attainment',ev)
        decision.update(reviewer='synthetic-author',reason='反馈声称不一致，但展示的Claude达成与输入已达成一致；其余模型没有给出明确差异，保留同版逐点证据，不反向改判。',
                        form_notes='不认同本次不通过结论：Claude输入已达成，质检解释同样达成；保留逐点原文证据，请复核实际差异。')
        decision['evidence']=[{'source':'feedback','quote':'Claude满足全部决定性考点'},
                              {'source':'input','field':'Claude是否达成','quote':'已达成'}]
        return ev,decision
    def test_question_check_before_points_then_freeze(self):
        with self.assertRaisesRegex(Error,'题目难度|qa-run question'):freeze(self.root,self.q)
        early=copy.deepcopy(self.q);early.pop('points');early.pop('design_profile');early.pop('author_notes')
        value,send=self.run_check('question',q=early)
        self.assertEqual(value['state'],'passed');send.assert_called_once()
        diversity.accept(self.root,self.q);freeze(self.root,self.q)
    def test_new_tasks_default_to_required_checks(self):
        from llm_authoring.workspace import create_task
        other=Path(create_task(self.ws,'latest')['task'])
        self.assertTrue(qa.required(other));self.assertFalse(qa.required(self.b))
    def test_question_input_change_invalidates_pass_and_stops_freeze(self):
        self.run_check('question',q=self.q)
        for key in ('prompt','insight'):
            q=copy.deepcopy(self.q)
            if key=='prompt':q[key]+='请说明。'
            else:q[key]['mechanism']+='新的机制。'
            with self.assertRaisesRegex(Error,'qa-run question'):freeze(self.root,q)
    def test_cache_reuses_same_result_without_cookie_or_network(self):
        self.run_check('question',q=self.q);Path(self.files['cookie_file']).write_text('')
        value,send=self.run_check('question',q=self.q)
        self.assertTrue(value['cached']);send.assert_not_called()
        with self.assertRaisesRegex(Error,'Cookie'):self.run_check('question',q=self.q,refresh=True)
    def test_login_expiry_is_not_failure_and_next_explicit_run_can_resume(self):
        with patch('llm_authoring.platform_client.call',return_value={'http_status':401,'response_text':'login first'}):
            result=qa.run(self.root,'question',q=self.q)
        self.assertEqual(result['state'],'needs_cookie');self.assertFalse(result['accepted'])
        self.assertTrue(Path(result['cookie_file']).is_file())
        value,send=self.run_check('question',q=self.q);send.assert_called_once();self.assertTrue(value['accepted'])
        self.assertEqual(len(list((self.root/'platform-checks').glob('question-*'))),2)
    def test_http_success_is_not_quality_success(self):
        value=response('question','不通过');self.assertEqual(qa.parse_response('question',value)['state'],'failed')
        value['response_text']=json.dumps({'BaseResp':{'StatusCode':9},'response':json.dumps({'题目AI质检结论':'通过','题目AI质检详情':'test'})})
        self.assertEqual(qa.parse_response('question',value)['state'],'service_error')
        for value in ({'http_status':200,'response_text':'{}'},{'http_status':200,'response_text':'not JSON'},
                      {'http_status':200,'response_text':json.dumps({'BaseResp':{'StatusCode':False},'response':'{}'})}):
            self.assertNotEqual(qa.parse_response('question',value)['state'],'passed')
    def test_three_complete_replies_and_judgments_required(self):
        self.frozen()
        with self.assertRaises(Error):self.run_check('criteria')
        self.assertFalse(list((self.root/'platform-checks').glob('criteria-*')))
    def test_failed_criteria_does_not_block_attainment_but_blocks_arena(self):
        self.frozen();ev=self.three();self.run_check('criteria',ev=ev,decision='不通过',details='缺少题面约束考点。')
        self.assertEqual(self.run_check('attainment',ev=ev)[0]['state'],'passed')
        with self.assertRaisesRegex(Error,'criteria'):prepare_arena(self.root,ev)
    def test_judgment_notes_change_invalidates_only_attainment(self):
        ev=self.completed();ev['models']['gpt']['points']['D1']['reason']+='补充解释。'
        self.assertTrue(qa.stage_gate(self.root,'criteria',ev)['accepted'])
        with self.assertRaisesRegex(Error,'attainment'):qa.final_gate(self.root,ev)
        self.run_check('attainment',ev=ev);self.assertTrue(qa.final_gate(self.root,ev))
    def test_frozen_rubric_change_invalidates_later_checks(self):
        ev=self.completed();q=copy.deepcopy(self.q);q['points'][0]['criterion']+='补充边界。'
        diversity.accept(self.root,q);freeze(self.root,q)
        from llm_authoring.authoring import evaluation_template
        updated=evaluation_template(self.root);updated['reviewer']=ev['reviewer'];updated['models']=ev['models']
        with self.assertRaisesRegex(Error,'criteria'):qa.final_gate(self.root,updated)
    def test_evidence_based_disagreement_keeps_server_failure(self):
        ev,decision=self.disputed();result=qa.disagree(self.root,decision,ev)
        self.assertEqual(result['server_conclusion'],'不通过');self.assertIn('不认同',result['message'])
        self.assertTrue(Path(result['notes_file']).is_file())
        checks=qa.final_gate(self.root,ev);self.assertEqual(checks['attainment']['state'],'disputed')
        self.assertEqual(checks['attainment']['server_conclusion'],'不通过')
        self.assertTrue(qa.status(self.root,ev)['ready_for_arena'])
    def test_legacy_disagreement_notes_remain_valid_without_rewriting(self):
        ev,decision=self.disputed();decision.pop('notes_format_version')
        result=qa.disagree(self.root,decision,ev);original=Path(result['notes_file']).read_bytes()
        self.assertEqual(qa.final_gate(self.root,ev)['attainment']['state'],'disputed')
        self.assertEqual(Path(result['notes_file']).read_bytes(),original)
    def test_disagreement_needs_exact_feedback_and_input_evidence(self):
        ev,decision=self.disputed();decision['evidence'][1]['quote']='不存在的原文'
        with self.assertRaisesRegex(Error,'准确原文'):qa.disagree(self.root,decision,ev)
        self.assertFalse(qa.status(self.root,ev)['ready_for_arena'])
    def test_disagreement_cannot_waive_login_or_changed_input(self):
        ev,decision=self.disputed();ev['models']['claude']['points']['D1']['reason']+='新解释。'
        with self.assertRaises(Error):qa.disagree(self.root,decision,ev)
        self.assertEqual(qa.parse_response('attainment',{'http_status':403,'response_text':''})['state'],'needs_cookie')
        with self.assertRaises(Error):qa.disagreement_template(self.root,'question',ev,q=self.q)
    def test_import_requires_current_evaluation_and_rechecks_gates(self):
        ev=self.completed();fill_slots(self.root,ev)
        with self.assertRaisesRegex(Error,'显式提供'):import_arena(self.root)
        changed=copy.deepcopy(ev);changed['models']['gpt']['points']['D1']['reason']+='改变。'
        with self.assertRaisesRegex(Error,'attainment'):import_arena(self.root,changed)
        import_arena(self.root,ev)
    def test_six_markdown_delivery_carries_disagreement_but_no_credentials(self):
        ev,decision=self.disputed();qa.disagree(self.root,decision,ev);five=fill_five(self.root,ev)
        review=self_review_template(self.root);review['reviewer']='synthetic-test'
        for value in review['checks'].values():value.update(passed=True,reason='合成流程验证。')
        output=self.root/'delivery/v001';export_complete(self.root,five,review,ranking_template(self.root,five),output)
        self.assertIn(decision['form_notes'],(output/'提交信息.md').read_text())
        self.assertEqual(len(list(output.glob('*.md'))),1)
        self.assertEqual(len(list((output/'models').glob('*.md'))),5)
        for role,item in read_json(output/'fields.json')['models'].items():
            self.assertEqual((output/item['reply_file']).read_bytes(),(read_response(self.root,role)['directory']/'reply.md').read_bytes())
        self.assertNotIn('TEST-ONLY-CREDENTIAL',''.join(p.read_text() for p in output.rglob('*.json')))
    def test_record_tamper_detected_instead_of_accepting_a_forged_pass(self):
        self.frozen();ev=self.three();result,_=self.run_check('criteria',ev=ev)
        path=Path(result['attempt'])/'result.json';record=read_json(path);record['parsed']['state']='failed';write_json(path,record)
        with self.assertRaisesRegex(Error,'绑定'):qa.stage_gate(self.root,'criteria',ev)
    def test_simultaneous_disagreements_publish_only_one_consistent_decision(self):
        ev,decision=self.disputed();barrier=Barrier(2)
        def submit():
            barrier.wait()
            try:return qa.disagree(self.root,decision,ev)['state']
            except Error:return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:submit(),range(2)))
        self.assertEqual(sorted(results),['blocked','disputed'])
        self.assertEqual(qa.final_gate(self.root,ev)['attainment']['state'],'disputed')
    def test_returned_but_unpersisted_result_blocks_same_input_replay(self):
        original=write_json
        def fail_result(path,value):
            if Path(path).name=='result.json':raise OSError('synthetic disk failure')
            return original(path,value)
        with patch('llm_authoring.platform_checks.write_json',side_effect=fail_result):
            with self.assertRaises(OSError):self.run_check('question',q=self.q)
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error,'结果未知'):qa.run(self.root,'question',q=self.q)
            send.assert_not_called()
        self.assertTrue(list((self.root/'platform-checks').glob('question-*/intent.json')))
    def test_simultaneous_checks_do_not_duplicate_the_service_request(self):
        entered=Event();release=Event()
        def slow_call(*args):
            entered.set();release.wait(timeout=5);return response('question')
        with patch('llm_authoring.platform_client.call',side_effect=slow_call) as send:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(qa.run,self.root,'question',self.q)
                self.assertTrue(entered.wait(timeout=3))
                try:
                    with self.assertRaises(Error):qa.run(self.root,'question',q=self.q)
                finally:release.set()
                self.assertTrue(first.result()['accepted'])
            send.assert_called_once()
    def test_cache_is_checked_again_after_taking_the_lock(self):
        self.run_check('question',q=self.q);request,_,_=qa.descriptor(self.root,'question',q=self.q)
        existing=qa.latest(self.root,request)
        with patch('llm_authoring.platform_checks.latest',side_effect=[None,existing]),patch('llm_authoring.platform_client.call') as send:
            result=qa.run(self.root,'question',q=self.q)
        self.assertTrue(result['cached']);send.assert_not_called()
    def test_cli_check_and_status_expose_feedback_without_login_secret(self):
        from llm_authoring.cli import main
        write_json(self.root/'drafts/question.json',self.q)
        args=['--workspace',str(self.ws),'--task',str(self.root)]
        output=StringIO()
        with patch('llm_authoring.platform_client.call',return_value=response('question')),redirect_stdout(output),redirect_stderr(StringIO()):
            self.assertEqual(main(args+['qa-run','question']),0)
            self.assertEqual(main(args+['qa-status']),0)
        self.assertIn('passed',output.getvalue());self.assertNotIn('TEST-ONLY-CREDENTIAL',output.getvalue())
    def test_disagreement_write_failure_does_not_publish_acceptance(self):
        ev,decision=self.disputed();original=write_json
        def fail_decision(path,value):
            if Path(path).name.startswith('disagreement-'):raise OSError('synthetic write failure')
            return original(path,value)
        with patch('llm_authoring.platform_checks.write_json',side_effect=fail_decision):
            with self.assertRaises(OSError):qa.disagree(self.root,decision,ev)
        self.assertFalse(qa.status(self.root,ev)['ready_for_arena'])
        self.assertTrue(qa.disagree(self.root,decision,ev)['accepted_with_evidence'])
    def test_latest_login_error_after_explicit_refresh_does_not_reuse_old_pass(self):
        self.run_check('question',q=self.q)
        with patch('llm_authoring.platform_client.call',return_value={'http_status':401,'response_text':''}):
            self.assertEqual(qa.run(self.root,'question',q=self.q,refresh=True)['state'],'needs_cookie')
        with self.assertRaisesRegex(Error,'qa-run question'):qa.question_gate(self.root,self.q)
