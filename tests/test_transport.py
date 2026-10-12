import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
from llm_authoring.providers import collect, read_api_body, request_deadline
from llm_authoring.core import freeze, read_response, write_json

class TerminalReadTest(unittest.TestCase):
    def test_completed_event_does_not_wait_for_eof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root/"REQUEST.json", {"question_type":"How-to类"})
            freeze(root, {'schema_version':1,'task_id':'diagnostic-terminal','prompt':'连接检查，请只回复OK。','question_type':'How-to类',
                          'insight':{'mechanism':'连接检查','priority':'完成','conclusion':'OK'},'author_notes':'诊断夹具，不是正式题目。',
                          'points':[{'id':'D1','kind':'decisive','criterion':'回复OK'}]})
            config = root/'providers.json'
            config.write_text(json.dumps({'schema_version':1,'providers':{'gpt':{'display_name':'GPT-5.6 sol','protocol':'responses',
                'base_url':'https://example.com/v1/responses','model':'gpt-5.6-sol','api_key':'private-test-fixture',
                'request_options':{'max_output_tokens':1000,'reasoning':{'effort':'high'}}}}}))
            config.chmod(0o600)
            data = {'status':'completed','model':'gpt-5.6-sol','output':[{'type':'message','content':[{'type':'output_text','text':'OK'}]}]}
            raw = ('data: '+json.dumps({'type':'response.completed','response':data})+'\n\n').encode()
            class Reply:
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def read(self,*args): raise TimeoutError('completion received, server keeps connection open')
                def read1(self,*args):
                    if not hasattr(self,'sent'):self.sent=True;return raw
                    raise TimeoutError('reader requested bytes after completed event')
            class Opener:
                def open(self,*args,**kwargs): return Reply()
            with patch('urllib.request.build_opener',return_value=Opener()):
                collect(root,config,'gpt',allow_live=True)
            self.assertEqual(read_response(root,'gpt')['text'],'OK')

class TransportBoundaryTests(unittest.TestCase):
    def test_split_crlf_completed_event_and_utf8_are_preserved(self):
        event={'type':'response.completed','response':{'status':'completed'}}
        raw=('data: '+json.dumps(event,ensure_ascii=False)+'\r\n\r\n').encode()
        pieces=[raw[:-3],raw[-3:-2],raw[-2:]]
        class Reply:
            def read(self,*args):raise AssertionError('must use incremental reads')
            def read1(self,*args):
                if pieces:return pieces.pop(0)
                raise TimeoutError('read after terminal event')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'raw.sse';state={}
            result=read_api_body(Reply(),path,'private-fixture-key','sse',state,lambda:None)
            self.assertEqual(result,raw);self.assertEqual(path.read_bytes(),raw)
            self.assertEqual(state['terminal_event_type'],'response.completed')

    def test_failed_event_does_not_wait_for_connection_close(self):
        raw=b'data: {"type":"response.failed","response":{"status":"failed"}}\n\n'
        class Reply:
            def read(self,*args):raise AssertionError('must use incremental reads')
            def read1(self,*args):
                if not hasattr(self,'sent'):self.sent=True;return raw
                raise TimeoutError('read after failure event')
        with tempfile.TemporaryDirectory() as tmp:
            state={};path=Path(tmp)/'raw.sse'
            self.assertEqual(read_api_body(Reply(),path,'private-fixture-key','sse',state,lambda:None),raw)
            self.assertEqual(state['terminal_event_type'],'response.failed')

    def test_transport_failure_preserves_received_partial_stream(self):
        raw=b'data: {"type":"response.in_progress"}\n\n'
        class Reply:
            def read(self,*args):raise AssertionError('must use incremental reads')
            def read1(self,*args):
                if not hasattr(self,'sent'):self.sent=True;return raw
                raise TimeoutError('socket timeout')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'raw.sse'
            with self.assertRaises(TimeoutError):read_api_body(Reply(),path,'private-fixture-key','sse',{},lambda:None)
            self.assertEqual(path.read_bytes(),raw)

    def test_heartbeats_cannot_extend_total_deadline(self):
        import time
        class Reply:
            def read(self,*args):raise AssertionError('must use incremental reads')
            def read1(self,*args):time.sleep(.01);return b': ping\n\n'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'raw.sse';started=time.monotonic()
            with self.assertRaisesRegex(TimeoutError,'request_total_deadline'):
                with request_deadline(.06):read_api_body(Reply(),path,'private-fixture-key','sse',{},lambda:None)
            self.assertLess(time.monotonic()-started,1)
            self.assertIn(b': ping',path.read_bytes())

    def test_echoed_credential_split_across_chunks_removes_partial_file(self):
        key='private-fixture-key';pieces=[b'data: private-',b'fixture-key\n\n']
        class Reply:
            def read(self,*args):raise AssertionError('must use incremental reads')
            def read1(self,*args):return pieces.pop(0)
        from llm_authoring.core import Error
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'raw.sse'
            with self.assertRaisesRegex(Error,'凭据'):read_api_body(Reply(),path,key,'sse',{},lambda:None)
            self.assertFalse(path.exists())

if __name__ == '__main__': unittest.main()
