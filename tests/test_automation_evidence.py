"""Synthetic recipe receipts and mixed-source delivery; no network/model calls."""
from pathlib import Path
import tempfile
import unittest
import json
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from llm_authoring.core import Error, hash_json, read_json, write_json, sha, read_response
from llm_authoring.authoring import check_three, self_review_template
from llm_authoring.automation_evidence import platform_fields, web_evidence, screenshot_evidence, capture_source
from llm_authoring.ranking import export_complete, ranking_template, check_five
import test_manual as fixture_module
from test_arena_ranking import fill_five
from test_piweb_import import bridge


class AutomationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.ManualTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root
        task = read_json(self.root/'TASK.json'); task['platform_checks_required'] = False
        write_json(self.root/'TASK.json',task)
        self.evaluation = self.fixture.three()
        self.expected = platform_fields(self.root,self.evaluation)

    def check_record(self,name='check',key='attainment',conclusion='不通过'):
        directory = self.root/'platform-web'/name
        payload = self.expected if key!='insight' else {'values':{k:self.expected['values'][k] for k in ('question-input','insight-input')},'selections':{k:self.expected['selections'][k] for k in ('question-type-radio','question-domain-select')}}
        write_json(directory/'input.json',{'kind':'checks','itemId':'123','version':'r0001','keys':[key], 'input':payload,'inputHash':hash_json(payload)})
        write_json(directory/(key+'-intent.json'),{'prior':{'calls':0}})
        write_json(directory/(key+'-dispatch.json'),{'after':{'running':True,'calls':1}})
        from llm_authoring.automation_evidence import _subset
        receipt={'inputHash':hash_json(_subset(payload,key)), 'observed':{'key':key,'running':False,'calls':1,'observation':'result_visible','conclusion':conclusion,'resultText':'synthetic result'},'completedAt':'2026-10-27T01:00:00Z'}
        write_json(directory/(key+'-result.json'),receipt)
        return directory

    def test_bound_results_old_version_reuse_and_unresolved_later_call(self):
        self.check_record(key='insight',conclusion='通过')
        self.assertEqual(web_evidence(self.root,self.expected)['checks']['insight']['state'],'passed')
        changed={'values':{**self.expected['values'],'insight-description-input':'new rubric'},'selections':self.expected['selections']}
        self.assertEqual(web_evidence(self.root,changed)['checks']['insight']['state'],'passed')
        self.check_record('attainment')
        self.assertEqual(web_evidence(self.root,self.expected)['checks']['attainment']['state'],'failed')
        self.assertEqual(web_evidence(self.root,changed)['checks']['attainment']['state'],'not_verified')
        directory=self.check_record('unknown');(directory/'attainment-result.json').unlink()
        self.assertEqual(web_evidence(self.root,self.expected)['checks']['attainment']['state'],'unknown')

    def test_tampered_input_is_not_silently_exported(self):
        directory=self.check_record()
        binding=read_json(directory/'input.json');binding['input']['values']['question-input']='edited'
        write_json(directory/'input.json',binding)
        with self.assertRaisesRegex(Error,'哈希'):web_evidence(self.root,self.expected)

    def test_platform_fields_cli_reuses_evaluation_and_existing_gate(self):
        from llm_authoring.cli import main
        ev_path=self.root/'evaluations/three.json';write_json(ev_path,self.evaluation)
        output=StringIO()
        args=['--workspace',str(self.fixture.workspace),'--task',str(self.root),'platform-fields','--evaluation',str(ev_path)]
        with redirect_stdout(output):self.assertEqual(main(args),0)
        self.assertEqual(json.loads(output.getvalue()),self.expected)
        for judgment in self.evaluation['models']['seed']['points'].values():
            judgment.update(met=True,quotes=['先核对验收依据'])
        write_json(ev_path,self.evaluation)
        with redirect_stderr(StringIO()):self.assertEqual(main(args),2)

    def test_one_export_includes_capture_web_dispute_and_manifest(self):
        directory=self.root/'platform-web/archive'
        directory.mkdir(parents=True)
        item=read_response(self.root,'seed')
        (directory/'reply.md').write_bytes((item['directory']/'reply.md').read_bytes())
        write_json(directory/'session.json',{})
        result={'role':'seed','version':'r0001','sessionId':'user-session','stopReason':'stop',
                'promptHash':bridge.digest(self.fixture.q['prompt'].encode()),'replyHash':sha(directory/'reply.md'),
                'sessionHash':sha(directory/'session.json'),'sourceKind':'piweb_user','thinkingLevel':'high',
                'model':{'displayName':'seed-2.1-turbo'}}
        write_json(directory/'result.json',result)
        write_json(directory/'receive-intent.json',{**result,'kind':'receive'})
        bridge.import_archive(self.root,directory)
        self.assertEqual(capture_source(self.root,'seed')['kind'],'piweb_user')
        check=self.check_record()
        feedback=self.root/'platform-web/feedback'
        write_json(feedback/'input.json',{'kind':'feedback','itemId':'123','key':'attainment','checkCalls':1,
                   'resultHash':bridge.digest(b'synthetic result'),'note':'有证据的异议，保留不通过。'})
        write_json(feedback/'result.json',{'status':'saved','label':'正常','note':'有证据的异议，保留不通过。'})
        five=fill_five(self.root,self.evaluation)
        review=self_review_template(self.root);review['reviewer']='synthetic'
        for item in review['checks'].values():item.update(passed=True,reason='Synthetic professional self-review.')
        output=self.root/'delivery/new'
        export_complete(self.root,five,review,ranking_template(self.root,five),output)
        fields=read_json(output/'fields.json')
        self.assertEqual(fields['web_checks']['checks']['attainment']['state'],'failed')
        text=(output/'提交信息.md').read_text(encoding='utf-8')
        self.assertIn('由用户获取',text);self.assertIn('有证据的异议',text)
        self.assertNotIn('前三份回复为用户提供',text)
        for name,digest in read_json(output/'manifest.json')['files'].items():self.assertEqual(sha(output/name),digest)
        self.assertFalse(screenshot_evidence(self.root)['seed']['generated'])
