import copy
import hashlib
from pathlib import Path
import unittest
from PIL import Image,ImageDraw
from llm_authoring import official
from llm_authoring import browser_checks
from llm_authoring.core import Error,read_json,write_json,freeze,hash_json,sha,read_response,response_dir
from llm_authoring.authoring import evaluation_template,check_seed
from llm_authoring.manual import prepare_model,import_model
import test_browser_checks as browser_tests
import test_diversity as diversity


class OfficialClientTests(unittest.TestCase):
    candidate=browser_tests.BrowserChecksTests.candidate
    tearDown=browser_tests.BrowserChecksTests.tearDown
    observed_question=browser_tests.BrowserChecksTests.observed_question

    def setUp(self):
        browser_tests.BrowserChecksTests.setUp(self)
        task=read_json(self.root/'TASK.json')
        task['response_mode']='official_clients'
        task['model_contract']={role:{'model':m,'display_name':n,'effort':'high'} for role,(m,n) in official.MODELS.items()}
        write_json(self.root/'TASK.json',task)
        directory=self.observed_question()
        browser_checks.import_results(self.root,directory,q=self.q)
        diversity.accept(self.root,self.q);freeze(self.root,self.q)

    def seed_bundle(self,reply='这是合成测试回复。'):
        prepared=official.prepare(self.root,'seed')
        request=read_json(prepared['request']);run=Path(prepared['request']).parent/'run';run.mkdir()
        (run/'reply.md').write_text(reply)
        original={'source':'official_reply_copy_action','captured':reply,'previous_clipboard_read':False,'session_id':'12345'}
        write_json(run/'official-copy.json',original)
        write_json(run/'input-verified.json',{'input_verified':True,'model':'豆包 2.1 Pro\n高',
                   'prompt_readback':request['prompt'],'prompt_bytes_sha256':request['prompt_bytes_sha256'],
                   'request_sha256':hash_json(request)})
        write_json(run/'send-intent.json',{'request_sha256':hash_json(request)})
        write_json(run/'send-click.json',{'clicked':True,'model':'豆包 2.1 Pro\n高',
                   'prompt_readback':request['prompt'],'request_sha256':hash_json(request)})
        write_json(run/'conversation.json',{'session_id':'12345','request_sha256':hash_json(request)})
        generation={'request_sha256':hash_json(request),'prompt_bytes_sha256':request['prompt_bytes_sha256'],
                    'session_id':'12345','actual_model':'doubao-seed-2.1-pro','actual_effort':'high',
                    'reply_sha256':sha(run/'reply.md'),'official_copy_sha256':sha(run/'official-copy.json'),
                    'input_verified_before_send':True,'rich_media_detected':False}
        write_json(run/'generation.json',generation)
        image=Image.new('RGB',(640,400),'white')
        ImageDraw.Draw(image).text((20,20),'SYNTHETIC TEST ONLY - NOT REAL CLIENT EVIDENCE',fill='black')
        image.save(run/'screen-001.png')
        capture={'request_sha256':hash_json(request),'generation_sha256':hash_json(generation),
                 'session_id':'12345','source':'real_official_webpage','frames':[
                     {'filename':'screen-001.png','sha256':sha(run/'screen-001.png'),
                      'source':'real_official_webpage','session_id':'12345'}]}
        write_json(run/'capture.json',capture)
        write_json(run/'verification.json',{'capture_sha256':hash_json(capture),'reviewer':'synthetic-test',
                   'model_and_effort_visible':True,'prompt_matches':True,'complete_reply_covered':True,
                   'actual_model':'doubao-seed-2.1-pro','actual_effort':'high','ending_quote':reply})
        return run

    def test_request_is_frozen_prompt_only_and_followups_require_seed(self):
        prepared=official.prepare(self.root,'seed')
        request=read_json(prepared['request'])
        self.assertEqual(Path(prepared['prompt_file']).read_bytes(),self.q['prompt'].encode())
        self.assertNotIn('format_instruction',request)
        self.assertEqual(request['prompt_bytes_sha256'],hashlib.sha256(self.q['prompt'].encode()).hexdigest())
        with self.assertRaises(Error):official.prepare(self.root,'gpt')
        self.assertFalse((self.root/'client-input'/request['prompt_sha256']/'gpt').exists())

    def test_manual_imports_are_blocked_in_client_mode(self):
        with self.assertRaisesRegex(Error,'官方客户端'):prepare_model(self.root,'seed')
        with self.assertRaisesRegex(Error,'官方客户端'):import_model(self.root,'seed')
        self.assertFalse((self.root/'model-input').exists())

    def test_original_bundle_import_is_idempotent_and_can_be_scored(self):
        self.seed_bundle()
        result=official.import_result(self.root,'seed')
        self.assertTrue(result['complete'])
        original=read_response(self.root,'seed')
        self.assertEqual(original['meta']['source_kind'],'official_client_automation')
        self.assertEqual(original['meta']['display_name'],'Seed 2.1 Pro')
        before=(original['directory']/'metadata.json').read_bytes()
        self.assertTrue(official.import_result(self.root,'seed')['already_imported'])
        self.assertEqual((original['directory']/'metadata.json').read_bytes(),before)
        ev=evaluation_template(self.root,('seed',));ev['reviewer']='synthetic-review'
        for point in ev['models']['seed']['points'].values():point.update(met=False,reason='合成原文没有给出该判断。',quotes=[])
        self.assertTrue(check_seed(self.root,ev)['continue_to_gpt_claude'])
        write_json(self.root/'evaluations/seed-r0001.json',ev)
        prepared=official.prepare(self.root,'gpt')
        self.assertEqual(read_json(prepared['request'])['seed_response_sha256'],original['meta']['reply_sha256'])

    def test_missing_or_unreviewed_screenshot_never_creates_response(self):
        run=self.seed_bundle()
        review=read_json(run/'verification.json');review['complete_reply_covered']=False;write_json(run/'verification.json',review)
        with self.assertRaisesRegex(Error,'查看全部真实截图'):official.import_result(self.root,'seed')
        self.assertFalse(response_dir(self.root,'seed').exists())

    def test_wrong_model_and_changed_original_copy_are_rejected(self):
        run=self.seed_bundle()
        generation=read_json(run/'generation.json');generation['actual_model']='another-model';write_json(run/'generation.json',generation)
        with self.assertRaises(Error):official.import_result(self.root,'seed')
        generation['actual_model']='doubao-seed-2.1-pro';write_json(run/'generation.json',generation)
        (run/'official-copy.json').write_text('{}')
        with self.assertRaises(Error):official.import_result(self.root,'seed')

    def test_capture_files_remain_immutable_after_import(self):
        self.seed_bundle();official.import_result(self.root,'seed')
        target=response_dir(self.root,'seed')/'client-evidence/screen-001.png'
        target.write_bytes(target.read_bytes()+b'changed')
        with self.assertRaisesRegex(Error,'原证据已改变'):official.validate_evidence(self.root,'seed')

    def test_rich_media_is_retained_but_cannot_be_imported_as_plain_markdown(self):
        self.seed_bundle('这是图片：![合成](https://example.test/image.png)')
        with self.assertRaisesRegex(Error,'富媒体'):official.import_result(self.root,'seed')
        self.assertFalse(response_dir(self.root,'seed').exists())

    def test_standard_links_json_fences_and_text_diagrams_remain_supported(self):
        self.seed_bundle('参考[资料](https://example.test)。\n\n```json\n{"a":1}\n```\n\nA -> B\n')
        self.assertTrue(official.import_result(self.root,'seed')['complete'])

    def test_followup_dispatch_proof_rejects_a_fully_attained_seed(self):
        self.seed_bundle();official.import_result(self.root,'seed')
        seed=read_response(self.root,'seed')
        ev=evaluation_template(self.root,('seed',));ev['reviewer']='synthetic-review'
        for point in ev['models']['seed']['points'].values():point.update(met=False,reason='合成原文未给出判断。',quotes=[])
        write_json(self.root/'evaluations/seed-r0001.json',ev)
        prepared=official.prepare(self.root,'gpt');contract=read_json(prepared['request'])
        wrapper=read_json(self.root/'revisions/r0001/question.json')
        official.seed_dispatch_proof(contract,wrapper,ev,seed['text'],seed['meta']['reply_sha256'])
        bad=copy.deepcopy(ev)
        for point in bad['models']['seed']['points'].values():point.update(met=True,quotes=[seed['text']])
        changed=copy.deepcopy(contract);changed['seed_evaluation_sha256']=hash_json(bad)
        with self.assertRaisesRegex(Error,'Seed已经全部达成'):
            official.seed_dispatch_proof(changed,wrapper,bad,seed['text'],seed['meta']['reply_sha256'])

    def test_capture_question_and_review_are_bound_to_original_inputs(self):
        self.seed_bundle();official.import_result(self.root,'seed')
        item=read_response(self.root,'seed');contract=item['meta']['client_request']
        wrapper=read_json(item['directory']/'client-evidence/question-at-capture.json')
        wrapper['question']['points'][0]['criterion']+='篡改'
        with self.assertRaisesRegex(Error,'冻结标准'):
            official.captured_question(contract,wrapper)
        review=official.review_template(self.root,'seed')
        self.assertEqual(len(review['screenshots']),1)
        self.assertEqual(read_json(review['verification_file'])['reviewer'],'synthetic-test')


if __name__=='__main__':unittest.main()
