"""Rejected candidates never send either post-model quality request."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import copy,json,unittest
from llm_authoring import platform_checks as qa
from llm_authoring.cli import main
from llm_authoring.core import Error,write_json
from llm_authoring.workspace import find_authoring_evaluation
import test_platform_checks as fixtures


class ThreeModelQAGateTests(unittest.TestCase):
    setUp=fixtures.PlatformTests.setUp
    tearDown=fixtures.PlatformTests.tearDown
    candidate=fixtures.PlatformTests.candidate
    fill=fixtures.PlatformTests.fill
    seed=fixtures.PlatformTests.seed
    three=fixtures.PlatformTests.three
    run_check=fixtures.PlatformTests.run_check
    frozen=fixtures.PlatformTests.frozen

    def evaluation(self,seed=False,gpt=False,claude=False):
        self.frozen();ev=self.three()
        for role,met in (('seed',seed),('gpt',gpt),('claude',claude)):
            for item in ev['models'][role]['points'].values():
                item.update(met=met,reason='合成判断，用于验证门槛顺序。',quotes=['先核对验收依据'] if met else [])
        return ev

    def snapshot(self):
        return {str(p.relative_to(self.root)):p.read_bytes() for p in (self.root/'platform-checks').rglob('*') if p.is_file()}

    def test_both_followups_failed_block_pair_before_config_cookie_or_attempts(self):
        ev=self.evaluation();before=self.snapshot()
        with patch('llm_authoring.platform_client.call') as send,patch('llm_authoring.platform_client.configuration') as config,patch('llm_authoring.platform_client.load_cookie') as cookie:
            for refresh in (False,True):
                with self.assertRaisesRegex(Error,'不合格|重新选题'):qa.run_models(self.root,ev,refresh=refresh)
            send.assert_not_called();config.assert_not_called();cookie.assert_not_called()
        self.assertEqual(self.snapshot(),before)

    def test_single_stage_and_refresh_cannot_bypass_gate(self):
        ev=self.evaluation();before=self.snapshot()
        with patch('llm_authoring.platform_client.call') as send:
            for stage in ('criteria','attainment'):
                for refresh in (False,True):
                    with self.assertRaisesRegex(Error,'不合格|重新选题'):qa.run(self.root,stage,evaluation=ev,refresh=refresh)
            send.assert_not_called()
        self.assertEqual(self.snapshot(),before)

    def test_seed_attaining_all_points_also_blocks_both_checks(self):
        ev=self.evaluation(seed=True,gpt=True,claude=True)
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error,'不合格|重新选题'):qa.run_models(self.root,ev)
            send.assert_not_called()

    def test_either_followup_attainment_allows_two_requests(self):
        ev=self.evaluation(gpt=True)
        for gpt,claude in ((True,False),(False,True),(True,True)):
            for role,met in (('gpt',gpt),('claude',claude)):
                for item in ev['models'][role]['points'].values():
                    item.update(met=met,quotes=['先核对验收依据'] if met else [])
            with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:fixtures.response('criteria' if p['plan_id']=='2' else 'attainment')) as send:
                self.assertTrue(qa.run_models(self.root,ev,refresh=True)['ready_for_arena'])
                self.assertEqual(send.call_count,2)

    def test_previously_passed_cache_cannot_override_failed_current_gate(self):
        ev=self.evaluation(gpt=True)
        with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:fixtures.response('criteria' if p['plan_id']=='2' else 'attainment')):
            qa.run_models(self.root,ev)
        before=self.snapshot()
        for item in ev['models']['gpt']['points'].values():item.update(met=False,quotes=[])
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error,'不合格|重新选题'):qa.run_models(self.root,ev)
            self.assertEqual(qa.status(self.root,ev)['stage'],'candidate_rejected')
            send.assert_not_called()
        self.assertEqual(self.snapshot(),before)

    def test_missing_or_stale_evaluation_never_sends(self):
        good=self.evaluation(gpt=True)
        stale=copy.deepcopy(good);stale['question_sha256']='stale'
        partial=copy.deepcopy(good);partial['models']['gpt']['points']['D1']['met']=None
        with patch('llm_authoring.platform_client.call') as send:
            for ev in (None,stale,partial):
                with self.assertRaises(Error):qa.run_models(self.root,ev)
            send.assert_not_called()

    def test_cli_pair_and_single_stages_report_local_rejection(self):
        ev=self.evaluation();file=self.root/'evaluations/three-r0001.json';write_json(file,ev)
        args=['--workspace',str(self.ws),'--task',str(self.root),'qa-run']
        with patch('llm_authoring.platform_client.call') as send:
            for stage in ('models','criteria','attainment'):
                error=StringIO()
                with redirect_stdout(StringIO()),redirect_stderr(error):
                    self.assertEqual(main(args+[stage,'--evaluation',str(file),'--refresh']),2)
                self.assertIn('重新选题',error.getvalue())
            send.assert_not_called()

    def test_status_recognizes_failed_evaluation_and_prompts_new_candidate(self):
        ev=self.evaluation();file=self.root/'evaluations/three-r0001.json';write_json(file,ev)
        self.assertIsNone(find_authoring_evaluation(self.root))
        self.assertEqual(find_authoring_evaluation(self.root,require_gate=False),file)
        with patch('llm_authoring.platform_client.call') as send:
            status=qa.status(self.root,ev);self.assertEqual(status['stage'],'candidate_rejected')
            self.assertFalse(status['ready_for_arena']);self.assertIn('重新选题',status['next'])
            for command in ('status','qa-status'):
                output=StringIO()
                with redirect_stdout(output):self.assertEqual(main(['--workspace',str(self.ws),'--task',str(self.root),command]),0)
                status=json.loads(output.getvalue());self.assertEqual(status['stage'],'candidate_rejected')
                self.assertFalse(status['three_model_gate']);self.assertIn('重新选题',status['next'])
            send.assert_not_called()

    def test_early_question_check_is_unaffected_by_model_gate(self):
        ev=self.evaluation()
        with patch('llm_authoring.platform_client.call',return_value=fixtures.response('question')) as send:
            self.assertEqual(qa.run(self.root,'question',q=self.q,evaluation=ev,refresh=True)['state'],'passed')
            send.assert_called_once()
