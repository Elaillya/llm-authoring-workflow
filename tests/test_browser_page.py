"""Synthetic page-only proof; no real check, screenshot or model is represented."""
from pathlib import Path
import copy,json,unittest
from PIL import Image,ImageDraw
from llm_authoring import browser_checks as browser,browser_page as page,platform_checks as qa
from llm_authoring.core import Error,read_json,write_json,hash_json,sha
import test_browser_checks as fixture

class PageReceiptTests(unittest.TestCase):
    setUp=fixture.BrowserChecksTests.setUp
    tearDown=fixture.BrowserChecksTests.tearDown
    candidate=fixture.BrowserChecksTests.candidate
    observed_question=fixture.BrowserChecksTests.observed_question
    def bundle(self,prepared=None,dirty=False,busy=False):
        prepared=prepared or browser.prepare(self.root,('question',),q=self.q)
        directory=Path(prepared['spec']).parent;spec=read_json(prepared['spec']);folder=directory/'dom-result';folder.mkdir()
        binding=spec['binding'];snapshot={'observed_at':'synthetic-test-time','location_binding':{'task_id':binding['task_id'],'item_id':binding['item_id'],'template_id':None,'template_type':None},'inputs':{k:v for k,v in spec['expected']['question']['params'].items() if k!='from_agentic'},'dirty':dirty,'busy':busy,'call_count':2,'result_text':'题目AI质检结论\n通过\n题目AI质检详情\n合成测试，无真实专业结论。'}
        for name in ['before.json','after.json']:write_json(folder/name,snapshot)
        for name in ['check-001.png','check-002.png']:
            image=Image.new('RGB',(640,400),'white');ImageDraw.Draw(image).text((10,10),'SYNTHETIC TEST ONLY',fill='black');image.save(folder/name)
        capture={'schema_version':1,'source':'genuine_current_platform_page','spec_sha256':hash_json(spec),'stage':'question','platform_binding':binding,'network_request_observed':False,'files':{n:sha(folder/n) for n in ['before.json','after.json','check-001.png','check-002.png']}}
        write_json(folder/'capture.json',capture);write_json(folder/'verification.json',{'capture_sha256':hash_json(capture),'reviewer':'synthetic fixture','inputs_and_fresh_result_verified':True,'screenshots_reviewed':['check-001.png','check-002.png']});return directory
    def test_page_result_unlocks_current_input_without_inventing_http(self):
        directory=self.bundle();result=page.import_result(self.root,directory,self.q)['question'];self.assertTrue(result['accepted'])
        _,record=qa.verified_record(Path(result['attempt']),'question');self.assertNotIn('http_status',record['transport']);self.assertNotIn('network_request_id',record['transport']);self.assertEqual(record['transport']['source'],page.SOURCE)
        self.assertTrue(qa.question_gate(self.root,self.q));before=(Path(result['attempt'])/'result.json').read_bytes();page.import_result(self.root,directory,self.q);self.assertEqual((Path(result['attempt'])/'result.json').read_bytes(),before)
    def test_page_recovery_keeps_prior_network_timeout_and_becomes_latest(self):
        original=self.observed_question(status=504,body='synthetic timeout');error=browser.import_results(self.root,original,q=self.q)['question'];old=(Path(error['attempt'])/'result.json').read_bytes();retry=browser.prepare(self.root,('question',),q=self.q,retry_reason='原请求已结束，页面原生结果随后可用');directory=self.bundle(retry);result=page.import_result(self.root,directory,self.q)['question'];self.assertTrue(result['accepted']);self.assertNotEqual(error['attempt'],result['attempt']);self.assertEqual((Path(error['attempt'])/'result.json').read_bytes(),old)
    def test_dirty_or_unreviewed_page_cannot_unlock(self):
        directory=self.bundle(dirty=True)
        with self.assertRaisesRegex(Error,'过期|变化|运行'):page.import_result(self.root,directory,self.q)
        review=read_json(directory/'dom-result/verification.json');review['screenshots_reviewed']=[];write_json(directory/'dom-result/verification.json',review)
        with self.assertRaisesRegex(Error,'逐张'):page.import_result(self.root,directory,self.q)
    def test_changed_input_or_item_rejects_saved_page(self):
        directory=self.bundle();changed=copy.deepcopy(self.q);changed['prompt']+='输入变化'
        with self.assertRaisesRegex(Error,'已变化'):page.import_result(self.root,directory,changed)
        binding=read_json(self.root/'browser/binding.json');binding['item_id']='201';write_json(self.root/'browser/binding.json',binding)
        with self.assertRaisesRegex(Error,'不属于'):page.import_result(self.root,directory,self.q)
    def test_changed_screenshot_after_import_invalidates_gate(self):
        directory=self.bundle();result=page.import_result(self.root,directory,self.q)['question'];(Path(result['attempt'])/'check-001.png').write_bytes(b'changed')
        with self.assertRaisesRegex(Error,'改写'):qa.question_gate(self.root,self.q)

    def test_busy_page_cannot_unlock(self):
        directory=self.bundle(busy=True)
        with self.assertRaisesRegex(Error,'运行'):page.import_result(self.root,directory,self.q)

    def test_result_changed_during_capture_cannot_unlock(self):
        directory=self.bundle();folder=directory/'dom-result';after=read_json(folder/'after.json');after['call_count']=3;write_json(folder/'after.json',after)
        capture=read_json(folder/'capture.json');capture['files']['after.json']=sha(folder/'after.json');write_json(folder/'capture.json',capture)
        review=read_json(folder/'verification.json');review['capture_sha256']=hash_json(capture);write_json(folder/'verification.json',review)
        with self.assertRaisesRegex(Error,'采集过程中'):page.import_result(self.root,directory,self.q)
