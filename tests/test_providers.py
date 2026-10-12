import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from llm_authoring.core import Error,freeze,read_response
from llm_authoring.providers import load_provider,make_payload,parse_response,collect,FORMAT,model_matches,recover,decode_raw
from test_core import question,prepared


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);prepared(self.root)
        self.config=self.root/'providers.json'
        self.profiles={'seed':{'display_name':'Seed 2.1 Turbo','protocol':'chat_completions','base_url':'https://example.com/v1/chat/completions','model':'doubao-seed-2.1-turbo','api_key':'private-fixture-key','request_options':{'max_tokens':1000}},
                       'gpt':{'display_name':'GPT-5.6 sol','protocol':'responses','base_url':'https://example.com/v1/chat/completions','model':'gpt-5.6-sol','api_key':'private-fixture-key','request_options':{'max_output_tokens':1000,'reasoning':{'effort':'high'}}}}
        self.config.write_text(json.dumps({'schema_version':1,'providers':self.profiles}));self.config.chmod(0o600)
    def tearDown(self): self.tmp.cleanup()
    def test_full_endpoint_wins_and_translates_gpt_options(self):
        p=load_provider(self.config,'gpt');payload=make_payload(p,'题目正文')
        self.assertEqual(p['effective_protocol'],'chat_completions')
        self.assertEqual(payload['reasoning_effort'],'high');self.assertEqual(payload['max_completion_tokens'],1000)
        self.assertEqual(payload['messages'],[{'role':'system','content':FORMAT},{'role':'user','content':'题目正文'}])
        self.assertNotIn('insight',json.dumps(payload))
    def test_public_config_is_refused(self):
        self.config.chmod(0o644)
        with self.assertRaisesRegex(Error,'权限'):load_provider(self.config,'seed')
    def test_prompt_override_is_refused(self):
        p=load_provider(self.config,'seed');p['request_options']['messages']=[]
        with self.assertRaisesRegex(Error,'覆盖'):make_payload(p,'题面')
    def test_truncation_and_refusal_are_not_scored(self):
        d={'model':'doubao-seed-2.1-turbo','choices':[{'message':{'content':'正文'},'finish_reason':'length'}]}
        self.assertEqual(parse_response('chat_completions',d)['completion_status'],'incomplete')
        d['choices'][0]['message']['refusal']='refusal'
        with self.assertRaisesRegex(Error,'拒绝'):parse_response('chat_completions',d)
    def test_response_and_claude_parsing_excludes_thinking(self):
        self.assertEqual(parse_response('responses',{'status':'completed','model':'gpt-5.6-sol','output':[{'type':'reasoning','summary':[]},{'type':'message','content':[{'type':'output_text','text':'# 答案'}]}]})['text'],'# 答案')
        self.assertEqual(parse_response('anthropic_messages',{'model':'claude-opus-4-6','stop_reason':'end_turn','content':[{'type':'thinking','thinking':'private'},{'type':'text','text':'# 答案'}]})['text'],'# 答案')
    def fake_opener(self,data):
        class Reply:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return json.dumps(data,ensure_ascii=False).encode()
        class Opener:
            def open(self,*args,**kwargs):return Reply()
        return Opener()
    def test_capture_preserves_bytes_and_never_repeats_paid_call(self):
        d={'id':'mock','model':'doubao-seed-2.1-turbo','choices':[{'message':{'content':'# 答案\n\n完整。\n'},'finish_reason':'stop'}]}
        with patch('urllib.request.build_opener',return_value=self.fake_opener(d)) as mock:
            collect(self.root,self.config,'seed',allow_live=True)
            self.assertEqual(read_response(self.root,'seed')['text'],'# 答案\n\n完整。\n')
            with self.assertRaisesRegex(Error,'已有回复'):collect(self.root,self.config,'seed',allow_live=True)
            self.assertEqual(mock.call_count,1)
        self.assertNotIn('private-fixture-key',''.join(p.read_text() for p in (self.root/'attempts').rglob('*.json')))
    def test_returned_model_substitution_blocks_capture(self):
        d={'model':'wrong-model','choices':[{'message':{'content':'答案'},'finish_reason':'stop'}]}
        with patch('urllib.request.build_opener',return_value=self.fake_opener(d)):
            with self.assertRaisesRegex(Error,'实际返回模型'):collect(self.root,self.config,'seed',allow_live=True)
        self.assertFalse((self.root/'responses').exists())
    def test_model_punctuation_alias_does_not_accept_other_version(self):
        self.assertTrue(model_matches('doubao-seed-2-1-turbo',['doubao-seed-2.1-turbo']))
        self.assertFalse(model_matches('doubao-seed-2-1-turbo-202601',['doubao-seed-2.1-turbo']))
    def test_responses_uses_gateway_compatible_input_list(self):
        p=load_provider(self.config,'gpt');p['effective_protocol']='responses'
        result=make_payload(p,'题面')
        self.assertEqual(result['input'],[{'role':'user','content':[{'type':'input_text','text':'题面'}]}])
        self.assertTrue(result['stream'])
    def test_sse_requires_full_terminal_response_and_preserves_text(self):
        d={'status':'completed','model':'gpt-5.6-sol','output':[{'type':'message','content':[{'type':'output_text','text':'# 完整\n\n答复。'}]}]}
        raw=('event: response.completed\ndata: '+json.dumps({'type':'response.completed','response':d},ensure_ascii=False)+'\n\ndata: [DONE]\n\n').encode()
        self.assertEqual(parse_response('responses',decode_raw('responses',raw,'sse'))['text'],'# 完整\n\n答复。')
        with self.assertRaisesRegex(Error,'completed'):decode_raw('responses',b'data: [DONE]\n\n','sse')
    def test_unknown_inflight_attempt_with_raw_cannot_be_retried(self):
        from llm_authoring.core import active_question,write_json
        directory=self.root/'attempts'/active_question(self.root)['prompt_sha256']/'seed';directory.mkdir(parents=True)
        write_json(directory/'a0001.json',{'status':'in_flight'})
        write_json(directory/'a0001.raw.json',{'model':'doubao-seed-2.1-turbo'})
        with self.assertRaisesRegex(Error,'状态未知'):collect(self.root,self.config,'seed',allow_live=True,retry_reason='不应重复扣费')
    def test_recovery_reuses_original_response_without_http(self):
        d={'model':'different','choices':[{'message':{'content':'# 原回复'},'finish_reason':'stop'}]}
        with patch('urllib.request.build_opener',return_value=self.fake_opener(d)):
            with self.assertRaises(Error):collect(self.root,self.config,'seed',allow_live=True)
        attempt=next((self.root/'attempts').rglob('a0001.json'))
        self.profiles['seed']['expected_response_models']=['different']
        self.config.write_text(json.dumps({'schema_version':1,'providers':self.profiles}))
        with patch('urllib.request.build_opener') as mock:
            recover(self.root,self.config,'seed',attempt);mock.assert_not_called()
        self.assertEqual(read_response(self.root,'seed')['text'],'# 原回复')


if __name__=='__main__':unittest.main()
