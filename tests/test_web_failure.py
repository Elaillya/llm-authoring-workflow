"""Synthetic browser evidence and authorized replacement, without model/network calls."""
from pathlib import Path
import unittest
import test_platform_checks as fixture
from llm_authoring import lessons, replacement, web_failure
from llm_authoring.core import Error, active_question, read_json, write_json, hash_json, read_response, freeze
from test_diversity import accept
from llm_authoring.text import insight_text


class WebFailureTests(unittest.TestCase):
    candidate=fixture.PlatformTests.candidate
    setUp=fixture.PlatformTests.setUp
    tearDown=fixture.PlatformTests.tearDown
    fill=fixture.PlatformTests.fill
    seed=fixture.PlatformTests.seed
    three=fixture.PlatformTests.three
    frozen=fixture.PlatformTests.frozen
    run_check=fixture.PlatformTests.run_check

    def evidence(self):
        task=read_json(self.root/'TASK.json'); task['platform_checks_required']=False;write_json(self.root/'TASK.json',task)
        accept(self.root,self.q);freeze(self.root,self.q);self.ev=self.three()
        frozen=active_question(self.root);q=frozen['question']
        values={'question-input':q['prompt'],'insight-input':insight_text(q['insight'])}
        for kind,field in [('decisive','insight-description-input'),('supporting','non-decisive-insight-description-input')]:
            values[field]='\n'.join(p['id']+'：'+p['criterion'] for p in q['points'] if p['kind']==kind) or '无'
        for role,field in [('seed','doubao'),('gpt','gpt56'),('claude','claude')]:
            values[field+'-markdown-input']=read_response(self.root,role)['text']
        payload={'values':values,'selections':{'question-domain-select':q['domain'],'question-type-radio':q['question_type'].removesuffix('类')}}
        self.directory=self.root/'platform-web'/'synthetic-check'
        write_json(self.directory/'input.json',{'kind':'checks','itemId':'synthetic-item','keys':['core-point'],'version':frozen['revision'],'input':payload,'inputHash':hash_json(payload)})
        write_json(self.directory/'core-point-intent.json',{'prior':{'key':'core-point','running':False,'calls':None}})
        write_json(self.directory/'core-point-dispatch.json',{'after':{'key':'core-point','running':True,'calls':1}})
        write_json(self.directory/'core-point-result.json',{'inputHash':hash_json(payload),'observed':{'key':'core-point','running':False,'needsRerun':False,'observation':'result_visible','conclusion':'不通过','calls':1,'resultText':'合成考点边界不清楚。'}})
        return self.directory

    def accepted(self):
        event=web_failure.register(self.root,self.evidence());eid=event['event_id']
        review=lessons.review_template(self.ws,eid)
        review.update(verdict='accepted',reviewer='synthetic',cause='边界不清',prevention='明确边界',applicability='合成场景',evidence_quotes=['合成考点边界不清楚。'])
        lessons.review(self.ws,review);return eid

    def test_web_replacement_keeps_original_and_other_roles(self):
        eid=self.accepted();before={r:read_response(self.root,r)['text'] for r in ('seed','gpt','claude')}
        plan=replacement.prepare(self.root,'gpt',eid,authorization_note='同意仅换GPT一次',reason='修标准后缺口仍在')
        Path(plan['input_file']).write_bytes('合成替换完整原文。\r\n'.encode())
        receipt=replacement.import_reply(self.root,'gpt',plan['replacement_id'])
        self.assertEqual((Path(receipt['archive'])/'reply.md').read_text(encoding='utf-8'),before['gpt'])
        for r in ('seed','claude'):self.assertEqual(read_response(self.root,r)['text'],before[r])
        self.assertEqual(read_response(self.root,'gpt')['text'],'合成替换完整原文。\r\n')
        self.assertTrue(replacement.import_reply(self.root,'gpt',plan['replacement_id'])['already_imported'])
        with self.assertRaisesRegex(Error,'授权已有'):
            replacement.prepare(self.root,'gpt',eid,authorization_note='同意仅换GPT一次',reason='再取一次')

    def test_unreviewed_and_tampered_evidence_cannot_authorize(self):
        eid=web_failure.register(self.root,self.evidence())['event_id']
        with self.assertRaisesRegex(Error,'认可'):
            replacement.prepare(self.root,'gpt',eid,authorization_note='同意',reason='缺口')
        review=lessons.review_template(self.ws,eid)
        review.update(verdict='accepted',reviewer='test',cause='边界',prevention='修复',applicability='合成',evidence_quotes=['合成考点边界不清楚。'])
        lessons.review(self.ws,review)
        path=self.directory/'core-point-result.json';v=read_json(path);v['observed']['resultText']='改写';write_json(path,v)
        with self.assertRaisesRegex(Error,'证据已变化'):
            replacement.prepare(self.root,'gpt',eid,authorization_note='同意',reason='缺口')

    def test_running_stale_or_unlinked_results_cannot_register(self):
        self.evidence();p=self.directory/'core-point-result.json';original=read_json(p)
        for key,value in [('running',True),('needsRerun',True),('conclusion','通过'),('calls',3)]:
            v=read_json(p);v['observed']=dict(original['observed'],**{key:value});write_json(p,v)
            with self.assertRaises(Error):web_failure.register(self.root,self.directory)
        write_json(p,original)
        v=read_json(self.directory/'input.json');v['input']['values']['gpt56-markdown-input']='different';v['inputHash']=hash_json(v['input']);write_json(self.directory/'input.json',v)
        original['inputHash']=v['inputHash'];write_json(p,original)
        with self.assertRaisesRegex(Error,'原文绑定'):web_failure.register(self.root,self.directory)

    def test_required_task_and_external_evidence_refused(self):
        self.evidence();task=read_json(self.root/'TASK.json');task['platform_checks_required']=True;write_json(self.root/'TASK.json',task)
        with self.assertRaisesRegex(Error,'自动化'):web_failure.register(self.root,self.directory)
        task['platform_checks_required']=False;write_json(self.root/'TASK.json',task)
        with self.assertRaisesRegex(Error,'当前任务'):web_failure.register(self.root,self.ws/'outside')
