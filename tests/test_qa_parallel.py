"""Batch concurrency and independent persistence with synthetic service replies."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier,Event
from unittest.mock import patch
import copy,unittest
from llm_authoring import platform_checks as qa
from llm_authoring.core import Error,write_json
import test_platform_checks as fixtures


class ParallelTests(unittest.TestCase):
    setUp=fixtures.PlatformTests.setUp
    tearDown=fixtures.PlatformTests.tearDown
    candidate=fixtures.PlatformTests.candidate
    fill=fixtures.PlatformTests.fill
    seed=fixtures.PlatformTests.seed
    three=fixtures.PlatformTests.three
    run_check=fixtures.PlatformTests.run_check
    frozen=fixtures.PlatformTests.frozen

    def test_batch_requests_overlap_and_each_gets_the_same_frozen_version(self):
        self.frozen();ev=self.three();barrier=Barrier(2);payloads=[]
        def service(config,payload,cookie):
            payloads.append(copy.deepcopy(payload));barrier.wait(timeout=5)
            return fixtures.response('criteria' if payload['plan_id']=='2' else 'attainment')
        with patch('llm_authoring.platform_client.call',side_effect=service) as send:
            result=qa.run_models(self.root,ev)
        self.assertEqual(send.call_count,2)
        self.assertEqual({v['state'] for v in result['checks'].values()},{'passed'})
        self.assertTrue(result['ready_for_arena'])
        self.assertEqual(payloads[0]['params']['题目'],payloads[1]['params']['题目'])

    def test_incomplete_model_judgments_stop_both_requests(self):
        self.frozen()
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaises(Error):qa.run_models(self.root,None)
            send.assert_not_called()
    def test_failed_criteria_still_returns_the_independent_attainment_check(self):
        self.frozen();ev=self.three()
        with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:
                fixtures.response('criteria',conclusion='不通过',details='缺少必要约束。') if p['plan_id']=='2' else fixtures.response('attainment')) as send:
            result=qa.run_models(self.root,ev)
        self.assertEqual(send.call_count,2)
        self.assertEqual(result['checks']['criteria']['state'],'failed')
        self.assertEqual(result['checks']['attainment']['state'],'passed')
        self.assertFalse(result['ready_for_arena'])

    def test_both_results_cached_and_partial_retry_only_sends_the_missing_stage(self):
        self.frozen();ev=self.three()
        with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:
                   fixtures.response('criteria') if p['plan_id']=='2' else {'http_status':401,'response_text':''}) as send:
            result=qa.run_models(self.root,ev)
        self.assertEqual(result['checks']['attainment']['state'],'needs_cookie')
        self.assertEqual(result['checks']['criteria']['state'],'passed')
        with patch('llm_authoring.platform_client.call',return_value=fixtures.response('attainment')) as send:
            result=qa.run_models(self.root,ev)
            send.assert_called_once();self.assertTrue(result['checks']['criteria']['cached'])
        with patch('llm_authoring.platform_client.call') as send:
            qa.run_models(self.root,ev);send.assert_not_called()

    def test_finished_stage_persists_while_the_other_is_still_waiting(self):
        self.frozen();ev=self.three();waiting=Event();release=Event();saved=Event();original=write_json
        def persist(path,value):
            original(path,value)
            if Path(path).name=='result.json' and value['binding']['stage']=='criteria':saved.set()
        def service(config,payload,cookie):
            if payload['plan_id']=='3':waiting.set();release.wait(timeout=5)
            return fixtures.response('criteria' if payload['plan_id']=='2' else 'attainment')
        with patch('llm_authoring.platform_client.call',side_effect=service),patch('llm_authoring.platform_checks.write_json',side_effect=persist):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(qa.run_models,self.root,ev)
                try:
                    self.assertTrue(waiting.wait(timeout=3));self.assertTrue(saved.wait(timeout=3))
                    request,_,_=qa.descriptor(self.root,'criteria',evaluation=ev)
                    self.assertEqual(qa.latest(self.root,request)['state'],'passed')
                    with self.assertRaises(Error):qa.run_models(self.root,ev)
                finally:release.set()
                self.assertTrue(future.result()['ready_for_arena'])

    def test_unknown_batch_attempt_never_resends_a_completed_or_unknown_request(self):
        self.frozen();ev=self.three();original=write_json
        def persist(path,value):
            if Path(path).name=='result.json' and value['binding']['stage']=='attainment':raise OSError('synthetic disk failure')
            original(path,value)
        with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:fixtures.response('criteria' if p['plan_id']=='2' else 'attainment')),patch('llm_authoring.platform_checks.write_json',side_effect=persist):
            with self.assertRaises(OSError):qa.run_models(self.root,ev)
        self.assertTrue(list((self.root/'platform-checks').glob('criteria-*/result.json')))
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error,'结果未知'):qa.run_models(self.root,ev,refresh=True)
            send.assert_not_called()

    def test_changed_judgment_only_invalidates_attainment_in_the_pair(self):
        self.frozen();ev=self.three()
        with patch('llm_authoring.platform_client.call',side_effect=lambda c,p,k:fixtures.response('criteria' if p['plan_id']=='2' else 'attainment')):qa.run_models(self.root,ev)
        ev['models']['gpt']['points']['D1']['reason']+='补充真实依据。'
        with patch('llm_authoring.platform_client.call',return_value=fixtures.response('attainment')) as send:
            qa.run_models(self.root,ev);send.assert_called_once()
