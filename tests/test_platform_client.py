"""Synthetic network/configuration safety, never actual credentials or service calls."""
from pathlib import Path
from unittest.mock import patch
import io,json,tempfile,unittest
from llm_authoring.core import Error
from llm_authoring.platform_client import ENDPOINT,KEYS,call,config_from_har,load_cookie,setup,validated_config


def config():
    return {'endpoint':ENDPOINT,'task_id':'123','checks':{stage:{'plan_id':str(i),'provider':2} for i,stage in enumerate(KEYS,1)}}


class Reply(io.BytesIO):
    code=200


class ClientTests(unittest.TestCase):
    def test_fixed_origin_rejects_exfiltration_and_header_injection(self):
        for change in ({'endpoint':'https://other.invalid/invoke'},{'referer':'https://other.invalid/'},
                       {'user_agent':'bad\r\nCookie: injected'}):
            with self.assertRaises(Error):validated_config({**config(),**change})
    def test_private_cookie_slot_and_existing_configuration_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'local').mkdir();result=setup(root,config())
            cookie=Path(result['cookie_file']);self.assertEqual(cookie.stat().st_mode&0o777,0o600)
            with self.assertRaises(Error):load_cookie(cookie)
            cookie.write_text('sid=TEST-ONLY-CREDENTIAL')
            self.assertEqual(load_cookie(cookie),'sid=TEST-ONLY-CREDENTIAL')
            setup(root,config());self.assertEqual(cookie.read_text(),'sid=TEST-ONLY-CREDENTIAL')
            with self.assertRaises(Error):setup(root,{**config(),'task_id':'456'})
    def test_cookie_permissions_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'local').mkdir();r=setup(root,config());cookie=Path(r['cookie_file'])
            cookie.write_text('sid=TEST-ONLY');cookie.chmod(0o644)
            with self.assertRaises(Error):load_cookie(cookie)
            cookie.chmod(0o600);link=root/'link';link.symlink_to(cookie)
            with self.assertRaises(Error):load_cookie(link)
    def test_conversion_header_and_cookie_runtime_only_without_retries(self):
        reply=Reply(b'{"example":true}')
        with patch('llm_authoring.platform_client.build_opener') as opener:
            opener.return_value.open.return_value=reply
            result=call(config(),{'plan_id':'1','provider':2,'params':{}},'sid=TEST-ONLY-CREDENTIAL')
            request=opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header('Agw-js-conv'),'str')
            self.assertEqual(request.get_header('Cookie'),'sid=TEST-ONLY-CREDENTIAL')
            self.assertIsNone(opener.return_value.open.call_args.kwargs['timeout'])
            opener.return_value.open.assert_called_once()
            self.assertNotIn('TEST-ONLY-CREDENTIAL',json.dumps(result))
    def test_legacy_timeout_cannot_reintroduce_a_wait_limit(self):
        for value in (None,30,360,900):
            self.assertIsNone(validated_config({**config(),'timeout_seconds':value})['timeout_seconds'])
        with patch('llm_authoring.platform_client.build_opener') as opener:
            opener.return_value.open.return_value=Reply(b'completed')
            call({**config(),'timeout_seconds':360},{},'sid=TEST-ONLY')
            self.assertIsNone(opener.return_value.open.call_args.kwargs['timeout'])
    def test_setup_legacy_timeout_is_idempotent_without_rewriting_private_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'local').mkdir();result=setup(root,config())
            target=Path(result['service_file']);old={**config(),'timeout_seconds':360};target.write_text(json.dumps(old))
            original=target.read_bytes();setup(root,old)
            self.assertEqual(target.read_bytes(),original)
    def test_credentials_echo_and_exception_text_are_not_logged(self):
        with patch('llm_authoring.platform_client.build_opener') as opener:
            opener.return_value.open.return_value=Reply(b'sid=TEST-ONLY-CREDENTIAL')
            self.assertNotIn('TEST-ONLY-CREDENTIAL',str(call(config(),{},'sid=TEST-ONLY-CREDENTIAL')))
            opener.return_value.open.side_effect=ValueError('sid=TEST-ONLY-CREDENTIAL')
            result=call(config(),{},'sid=TEST-ONLY-CREDENTIAL')
            self.assertEqual(result['transport_error'],'ValueError');self.assertNotIn('TEST-ONLY-CREDENTIAL',str(result))
    def test_capture_extracts_only_metadata_not_original_questions_or_cookie(self):
        with tempfile.TemporaryDirectory() as temp:
            entries=[]
            for i,(stage,(key,_)) in enumerate(KEYS.items(),1):
                entries.append({'request':{'method':'POST','url':ENDPOINT,'headers':[
                    {'name':'x-aidp-task-id','value':'123'},{'name':'Cookie','value':'TEST-ONLY-CREDENTIAL'}],
                    'postData':{'text':json.dumps({'plan_id':str(i),'provider':2,'params':{'题目':'PRIVATE-QUESTION'}})}},
                    'response':{'content':{'text':json.dumps({'response':json.dumps({key:'不通过'})})}}})
            path=Path(temp)/'capture.har';path.write_text(json.dumps({'log':{'entries':entries}}))
            result=config_from_har(path)
            self.assertEqual(result['task_id'],'123');self.assertEqual(len(result['checks']),3)
            self.assertNotIn('PRIVATE-QUESTION',str(result));self.assertNotIn('TEST-ONLY-CREDENTIAL',str(result))
