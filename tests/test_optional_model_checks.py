"""Synthetic user policy choices; never contact a model or platform."""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
import copy,json,unittest
import test_platform_checks as fixture
from llm_authoring import check_policy,platform_checks as qa
from llm_authoring.core import Error,read_json,write_json,read_response
from llm_authoring.manual import prepare_model
from llm_authoring.workspace import begin,create_task
from llm_authoring.arena import prepare_arena
from llm_authoring.authoring import self_review_template
from llm_authoring.ranking import export_complete,ranking_template
from test_arena_ranking import fill_five

class OptionalChecksTests(unittest.TestCase):
    setUp=fixture.PlatformTests.setUp
    tearDown=fixture.PlatformTests.tearDown
    candidate=fixture.PlatformTests.candidate
    fill=fixture.PlatformTests.fill
    seed=fixture.PlatformTests.seed
    three=fixture.PlatformTests.three
    frozen=fixture.PlatformTests.frozen
    run_check=fixture.PlatformTests.run_check
    def unset(self):
        task=read_json(self.root/'TASK.json');task.pop('model_checks_choice',None);write_json(self.root/'TASK.json',task)
    def skip(self):return check_policy.choose(self.root,'skipped','合成用户明确答复：不需要后两项质检。')
    def test_ask_once_after_seed_and_block_gpt_files_until_answered(self):
        self.unset();self.assertIsNone(check_policy.prompt(self.root));self.frozen()
        self.assertIsNone(check_policy.prompt(self.root));self.seed()
        self.assertEqual(begin(self.root,self.ws)['next_question']['field'],'model_checks_choice')
        with self.assertRaisesRegex(Error,'询问'):prepare_model(self.root,'gpt')
        self.skip();self.assertIsNone(check_policy.prompt(self.root))
        self.assertTrue(Path(prepare_model(self.root,'gpt')['input_file']).is_file())
    def test_new_and_other_tasks_do_not_inherit_choice(self):
        self.skip();other=Path(create_task(self.ws,'separate')['task'])
        self.assertIsNone(check_policy.current(other)['choice'])
        self.assertEqual(check_policy.current(self.root)['choice'],'skipped')
    def test_choice_requires_actual_note_and_is_append_only_and_bound(self):
        with self.assertRaisesRegex(Error,'明确'):check_policy.choose(self.root,'skipped','')
        prior=check_policy.current(self.root);new=self.skip()
        self.assertTrue(Path(prior['record']).is_file());self.assertTrue(Path(new['record']).is_file())
        self.assertEqual(new,self.skip())
        value=read_json(new['record']);value['choice']='required';write_json(new['record'],value)
        with self.assertRaisesRegex(Error,'绑定'):check_policy.current(self.root)
    def test_unanswered_choice_blocks_model_calls_and_arena(self):
        self.frozen();ev=self.three();self.unset()
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error,'询问'):qa.run_models(self.root,ev)
            with self.assertRaisesRegex(Error,'询问'):prepare_arena(self.root,ev)
            send.assert_not_called()
    def test_skip_all_entrypoints_including_refresh_and_no_postmodel_cache(self):
        self.frozen();ev=self.three();self.skip();original=qa.descriptor
        def descriptor(root,stage,*args,**kwargs):
            self.assertEqual(stage,'question');return original(root,stage,*args,**kwargs)
        with patch('llm_authoring.platform_client.call') as send,patch.object(qa,'descriptor',side_effect=descriptor):
            for stage in ('criteria','attainment'):
                for refresh in (False,True):self.assertEqual(qa.run(self.root,stage,evaluation=ev,refresh=refresh)['state'],'skipped_by_user')
            result=qa.run_models(self.root,ev,refresh=True)
            self.assertTrue(result['ready_for_arena']);send.assert_not_called()
            self.assertEqual({v['state'] for v in result['checks'].values()},{'skipped_by_user'})
    def test_skipped_checks_still_block_false_three_model_gate(self):
        self.frozen();ev=self.three();self.skip()
        for role in ('gpt','claude'):
            for j in ev['models'][role]['points'].values():j.update(met=False,quotes=[])
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaises(Error):qa.run_models(self.root,ev)
            with self.assertRaises(Error):prepare_arena(self.root,ev)
            self.assertFalse(qa.status(self.root,ev)['ready_for_arena']);send.assert_not_called()
    def test_question_check_remains_required_even_after_skip(self):
        self.frozen();ev=self.three();self.skip()
        self.run_check('question',q=self.q,decision='不通过',details='合成题目存在问题。',refresh=True)
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error,'qa-run question'):prepare_arena(self.root,ev)
            self.assertFalse(qa.status(self.root,ev)['ready_for_arena']);send.assert_not_called()
    def test_switch_after_service_error_preserves_record_and_skips_retry(self):
        self.frozen();ev=self.three()
        with patch('llm_authoring.platform_client.call',return_value={'http_status':503,'response_text':'temporary unavailable'}):
            failed=qa.run(self.root,'criteria',evaluation=ev)
        before=Path(failed['attempt'])/'result.json';raw=before.read_bytes();self.skip()
        with patch('llm_authoring.platform_client.call') as send:
            self.assertTrue(qa.status(self.root,ev)['ready_for_arena']);prepare_arena(self.root,ev);send.assert_not_called()
        self.assertEqual(before.read_bytes(),raw)
    def test_status_and_full_five_model_delivery_label_skip_and_keep_originals(self):
        self.frozen();ev=self.three();policy=self.skip()
        with patch('llm_authoring.platform_client.call') as send:
            five=fill_five(self.root,ev)
            review=self_review_template(self.root);review['reviewer']='synthetic-author'
            for c in review['checks'].values():c.update(passed=True,reason='仅为合成流程检查。')
            out=self.root/'delivery/skip';export_complete(self.root,five,review,ranking_template(self.root,five),out)
            send.assert_not_called()
        fields=read_json(out/'fields.json');checks=fields['platform_checks']['checks']
        self.assertEqual(checks['question']['state'],'passed')
        self.assertEqual(checks['criteria']['state'],'skipped_by_user');self.assertEqual(checks['attainment']['state'],'skipped_by_user')
        self.assertIn('未执行',(out/'提交信息.md').read_text())
        for role,model in fields['models'].items():self.assertEqual((out/model['reply_file']).read_bytes(),(read_response(self.root,role)['directory']/'reply.md').read_bytes())
        self.assertEqual(read_json(out/'evidence/platform/model-check-choice.json'),read_json(policy['record']))
    def test_change_back_to_required_restores_original_quality_gate(self):
        self.frozen();ev=self.three();self.skip()
        check_policy.choose(self.root,'required','合成用户改为需要检查。')
        self.assertFalse(qa.status(self.root,ev)['ready_for_arena'])
        with self.assertRaisesRegex(Error,'criteria'):prepare_arena(self.root,ev)
        result,_=self.run_check('criteria',ev=ev);self.assertEqual(result['state'],'passed')
        self.run_check('attainment',ev=ev);self.assertTrue(qa.status(self.root,ev)['ready_for_arena'])
    def test_workspace_update_preserves_unanswered_choice_and_does_not_prepare_arena(self):
        from llm_authoring.workspace import update_workspace
        self.frozen();ev=self.three();write_json(self.root/'evaluations/three-r0001.json',ev);self.unset()
        frozen=(self.root/'CURRENT.json').read_bytes();identity=(self.root/'TASK.json').read_bytes()
        with patch('llm_authoring.platform_client.call') as send:
            update_workspace(self.ws);send.assert_not_called()
        self.assertEqual((self.root/'CURRENT.json').read_bytes(),frozen)
        self.assertEqual((self.root/'TASK.json').read_bytes(),identity)
        self.assertFalse((self.root/'arena-input').exists())
    def test_choice_cannot_change_while_a_quality_request_holds_the_lock(self):
        previous=check_policy.current(self.root)
        with qa.check_lock(self.root):
            with self.assertRaisesRegex(Error,'运行'):self.skip()
        self.assertEqual(check_policy.current(self.root),previous)
    def test_choice_change_before_request_lock_prevents_network_and_cached_reuse(self):
        self.frozen();ev=self.three();original=qa.authoring_evaluation
        for cached in (False,True):
            check_policy.choose(self.root,'required','合成用户需要检查。')
            if cached:
                self.run_check('criteria',ev=ev);self.run_check('attainment',ev=ev)
            changed=False
            def evaluate(root,evaluation):
                nonlocal changed
                result=original(root,evaluation)
                if not changed:changed=True;self.skip()
                return result
            with patch.object(qa,'authoring_evaluation',side_effect=evaluate),patch('llm_authoring.platform_client.call') as send:
                result=qa.run_models(self.root,ev)
                self.assertEqual({r['state'] for r in result['checks'].values()},{'skipped_by_user'})
                send.assert_not_called()
    def test_policy_change_during_cache_preflight_is_blocked_by_same_lock(self):
        self.frozen();ev=self.three();original=qa.latest;attempted=False
        def latest(root,request):
            nonlocal attempted
            if request['stage']=='criteria' and not attempted:
                attempted=True
                with self.assertRaisesRegex(Error,'运行'):self.skip()
            return original(root,request)
        with patch.object(qa,'latest',side_effect=latest),patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:fixture.response('criteria' if p['plan_id']=='2' else 'attainment')) as send:
            result=qa.run_models(self.root,ev)
        self.assertTrue(attempted);self.assertEqual(send.call_count,2)
        self.assertTrue(result['ready_for_arena']);self.assertEqual(check_policy.current(self.root)['choice'],'required')
