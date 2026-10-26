"""Browser receipts use synthetic network events only; no live site/model calls."""
import copy
import json
import subprocess
import unittest
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from llm_authoring import browser_checks as browser
from llm_authoring import platform_checks as qa
from llm_authoring.core import Error, read_json, write_json
import test_platform_checks as platform_tests


class BrowserChecksTests(unittest.TestCase):
    candidate = platform_tests.PlatformTests.candidate
    tearDown = platform_tests.PlatformTests.tearDown

    def setUp(self):
        platform_tests.PlatformTests.setUp(self)
        task = read_json(self.root / 'TASK.json')
        task['platform_check_mode'] = 'browser'
        write_json(self.root / 'TASK.json', task)
        config = platform_tests.config()
        write_json(self.root / 'browser/binding.json', {
            'task_id': config['task_id'], 'item_id': '200',
            'template_id': '300', 'template_type': '1000'})

    def observed_question(self, decision='通过', *, prepared=None, status=200, body=None, request_id='synthetic-q'):
        prepared = prepared or browser.prepare(self.root, ('question',), q=self.q)
        spec = Path(prepared['spec'])
        module = Path(__file__).resolve().parents[1] / 'browser_automation/qa-observer.mjs'
        script = '''
import {readFile} from 'node:fs/promises';
import {CheckJournal, BrowserCheckObserver} from MODULE;
const spec=JSON.parse(await readFile(SPEC,'utf8'));
const journal=await CheckJournal.open(DIRECTORY,spec);
try {
 await journal.append({type:'intent',stage:'question'});
 const observer=new BrowserCheckObserver(journal,async()=>({body:BODY}));
 await observer.handle({method:'Network.requestWillBeSent',params:{requestId:REQUEST_ID,request:{url:'https://aidp.bytedance.com/llm/union/app/invoke',method:'POST',postData:JSON.stringify(spec.expected.question)}}});
 await observer.handle({method:'Network.responseReceived',params:{requestId:REQUEST_ID,response:{status:STATUS}}});
 await observer.handle({method:'Network.loadingFinished',params:{requestId:REQUEST_ID}});
} finally {await journal.close();}
'''
        substitutions = {'MODULE': module.as_uri(), 'SPEC': str(spec), 'DIRECTORY': prepared['journal'],
                         'BODY': platform_tests.response('question', decision)['response_text'] if body is None else body,
                         'REQUEST_ID':request_id,'STATUS':status}
        for key, value in substitutions.items():
            script = script.replace(key, json.dumps(value))
        subprocess.run(['node', '--input-type=module', '-'], input=script, text=True,
                       check=True, capture_output=True)
        return spec.parent

    def test_browser_task_blocks_direct_api_before_cookie_or_call(self):
        Path(self.files['cookie_file']).write_text('')
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error, '真实浏览器'):
                qa.run(self.root, 'question', q=self.q)
        send.assert_not_called()

    def test_node_journal_hashes_import_into_existing_gate_and_keep_browser_source(self):
        directory = self.observed_question()
        result = browser.import_results(self.root, directory, q=self.q)
        self.assertTrue(result['question']['accepted'])
        self.assertTrue(qa.question_gate(self.root, self.q))
        _, record = qa.verified_record(Path(result['question']['attempt']), 'question')
        self.assertEqual(record['transport']['source'], 'browser_network')
        self.assertEqual(record['transport']['platform_binding']['item_id'], '200')
        before = (Path(result['question']['attempt']) / 'result.json').read_bytes()
        browser.import_results(self.root, directory, q=self.q)
        self.assertEqual((Path(result['question']['attempt']) / 'result.json').read_bytes(), before)
        self.assertEqual(browser.prepare(self.root, ('question',), q=self.q)['new_checks'], 0)

    def test_real_failed_decision_does_not_become_a_pass_or_get_recalled(self):
        directory = self.observed_question('不通过')
        result = browser.import_results(self.root, directory, q=self.q)
        self.assertEqual(result['question']['state'], 'failed')
        self.assertFalse(result['question']['accepted'])
        with self.assertRaises(Error): qa.question_gate(self.root, self.q)
        self.assertEqual(browser.prepare(self.root, ('question',), q=self.q)['new_checks'], 0)

    def test_completed_service_retry_retains_both_receipts_and_latest_success(self):
        first=self.observed_question(status=504,body='gateway timeout')
        error=browser.import_results(self.root,first,q=self.q)['question']
        original=Path(error['attempt'])/'result.json';before=original.read_bytes()
        with self.assertRaisesRegex(Error,'retry-reason'):
            browser.prepare(self.root,('question',),q=self.q)
        retry=browser.prepare(self.root,('question',),q=self.q,retry_reason='原HTTP504已结束，原样重试一次')
        self.assertNotEqual(Path(retry['spec']).parent,first)
        self.assertEqual(read_json(retry['spec'])['expected'],read_json(first/'spec.json')['expected'])
        second=self.observed_question(prepared=retry,request_id='synthetic-retry')
        result=browser.import_results(self.root,second,q=self.q)['question']
        self.assertTrue(result['accepted']);self.assertNotEqual(result['attempt'],error['attempt'])
        self.assertEqual(original.read_bytes(),before)
        self.assertEqual(len(list((self.root/'platform-checks').glob('question-browser-*'))),2)
        browser.import_results(self.root,first,q=self.q)
        browser.import_results(self.root,second,q=self.q)
        self.assertEqual(len(list((self.root/'platform-checks').glob('question-browser-*'))),2)
        self.assertTrue(qa.question_gate(self.root,self.q))

    def test_retry_cannot_start_from_unknown_or_unimported_result(self):
        with self.assertRaisesRegex(Error,'完整完成回执'):
            browser.prepare(self.root,('question',),q=self.q,retry_reason='不能用这个理由重发未知请求')
        self.observed_question(status=504,body='gateway timeout')
        with self.assertRaisesRegex(Error,'完整完成回执'):
            browser.prepare(self.root,('question',),q=self.q,retry_reason='尚未导入')

    def test_retry_does_not_rerun_a_substantive_failed_or_passed_result(self):
        directory=self.observed_question('不通过');browser.import_results(self.root,directory,q=self.q)
        with self.assertRaisesRegex(Error,'有效专业结果'):
            browser.prepare(self.root,('question',),q=self.q,retry_reason='不允许刷结果')

    def test_completed_empty_response_can_retry_but_nonempty_unparsed_feedback_cannot(self):
        empty=json.dumps({'BaseResp':{'StatusCode':0},'response':'','session_id':''})
        directory=self.observed_question(body=empty);browser.import_results(self.root,directory,q=self.q)
        prepared=browser.prepare(self.root,('question',),q=self.q,retry_reason='完整回执明确为空')
        malformed=json.dumps({'BaseResp':{'StatusCode':0},'response':{'可能是专业意见':'先人工核对'}})
        second=self.observed_question(prepared=prepared,body=malformed,request_id='synthetic-malformed')
        browser.import_results(self.root,second,q=self.q)
        with self.assertRaisesRegex(Error,'人工核对'):
            browser.prepare(self.root,('question',),q=self.q,retry_reason='不能绕过尚未解释的意见')

    def test_legacy_single_receipt_is_preserved_when_retry_appends(self):
        directory=self.observed_question(status=503,body='service unavailable')
        result=browser.import_results(self.root,directory,q=self.q)['question']
        path=Path(result['attempt']);legacy=path.with_name(path.name.rsplit('-',1)[0]);path.rename(legacy)
        before=(legacy/'result.json').read_bytes()
        prepared=browser.prepare(self.root,('question',),q=self.q,retry_reason='原503已完成')
        second=self.observed_question(prepared=prepared,request_id='synthetic-after-legacy')
        self.assertTrue(browser.import_results(self.root,second,q=self.q)['question']['accepted'])
        self.assertEqual((legacy/'result.json').read_bytes(),before)

    def test_retry_requires_explicit_nonempty_reason(self):
        directory=self.observed_question(status=504,body='timeout');browser.import_results(self.root,directory,q=self.q)
        with self.assertRaisesRegex(Error,'说明'):
            browser.prepare(self.root,('question',),q=self.q,retry_reason='   ')

    def test_changing_retry_reason_cannot_duplicate_prepared_or_unimported_retry(self):
        directory=self.observed_question(status=504,body='timeout');browser.import_results(self.root,directory,q=self.q)
        first=browser.prepare(self.root,('question',),q=self.q,retry_reason='第一次明确重试')
        same=browser.prepare(self.root,('question',),q=self.q,retry_reason='换个理由也不能另开请求')
        self.assertEqual(first['spec'],same['spec']);self.assertTrue(same['existing_attempt'])
        self.observed_question(prepared=first,request_id='synthetic-original-retry')
        again=browser.prepare(self.root,('question',),q=self.q,retry_reason='已完成但未导入也必须先沿用')
        self.assertEqual(first['spec'],again['spec']);self.assertEqual(again['new_checks'],0)

    def test_changed_insight_or_item_cannot_reuse_old_network_result(self):
        directory = self.observed_question()
        browser.import_results(self.root, directory, q=self.q)
        changed = copy.deepcopy(self.q)
        changed['insight']['conclusion'] += '输入修改'
        with self.assertRaisesRegex(Error, '已变化'):
            browser.import_results(self.root, directory, q=changed)
        binding = read_json(self.root / 'browser/binding.json')
        binding['item_id'] = '201'
        write_json(self.root / 'browser/binding.json', binding)
        with self.assertRaisesRegex(Error, '不属于当前题目'):
            browser.import_results(self.root, directory, q=self.q)
        with self.assertRaises(Error):qa.question_gate(self.root,self.q)

    def test_edited_or_incomplete_browser_journal_cannot_unlock_the_gate(self):
        directory = self.observed_question()
        file = directory / 'journal/events.jsonl'
        file.write_text(file.read_text().replace('synthetic-q', 'changed-q'))
        with self.assertRaisesRegex(Error, '事件链'):
            browser.import_results(self.root, directory, q=self.q)
        with self.assertRaises(Error): qa.question_gate(self.root, self.q)

    def test_model_checks_remain_blocked_until_the_three_model_gate(self):
        with self.assertRaises(Error):
            browser.prepare(self.root, ('criteria', 'attainment'), evaluation={})
        self.assertFalse((self.root / 'browser-checks').exists())

    def test_workspace_can_start_at_real_question_number_without_an_extra_empty_task(self):
        from llm_authoring.workspace import create_workspace, default_task
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary)/'new-parent'
            create_workspace(parent,initial_task_id='1262',initial_task_folder='tasks/1262')
            self.assertEqual(default_task(parent),parent/'tasks/1262')
            self.assertEqual(read_json(parent/'tasks/1262/TASK.json')['task_id'],'1262')
            self.assertFalse((parent/'task').exists())

    def test_browser_cli_uses_pro_label_without_changing_other_tasks_model_names(self):
        from llm_authoring.cli import main
        from llm_authoring.core import NAMES
        original=NAMES.copy()
        output=StringIO()
        with redirect_stdout(output):
            status=main(['--workspace',str(self.ws),'--task',str(self.root),'begin'])
        self.assertEqual(status,0)
        self.assertEqual(json.loads(output.getvalue())['models']['seed']['display_name'],'Seed 2.1 Pro')
        self.assertEqual(NAMES,original)

    def test_sidebar_start_uses_browser_flow_and_requires_the_general_collector(self):
        from llm_authoring.cli import main
        output=StringIO()
        with redirect_stdout(output):
            status=main(['--workspace',str(self.ws),'--task',str(self.root),'start'])
        self.assertEqual(status,0)
        self.assertIn('浏览器出题流程',output.getvalue())
        self.assertIn('worker_protocol=2',output.getvalue())
        self.assertIn('不要求用户手工粘贴前三模型',output.getvalue())


if __name__ == '__main__':
    unittest.main()
