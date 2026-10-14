"""Domain selection, freeze binding, and historical task compatibility."""
import json
from pathlib import Path
import tempfile
import unittest
from llm_authoring.core import Error,active_question,freeze,hash_json,read_json,sha,write_json
from llm_authoring.workspace import begin,choose_domain,choose_type,create_task,create_workspace,update_workspace
from test_core import question


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.workspace=Path(self.temp.name)/'workspace'
        create_workspace(self.workspace)
        self.task=self.workspace/'task'
        # Preserve the v3 request format as a backwards-compatibility fixture.
        request=json.loads((self.task/'REQUEST.json').read_text());request.pop('selection_schema',None)
        (self.task/'REQUEST.json').write_text(json.dumps(request))
    def tearDown(self):self.temp.cleanup()
    def candidate(self,domain):
        q=question();q.update({'task_id':'question-001','domain':domain})
        return q
    def test_new_question_requires_user_domain_and_type(self):
        result=begin(self.task,self.workspace)
        self.assertIsNone(result['domain'])
        self.assertEqual(result['requires_input'],['domain','question_type'])
        self.assertIsNone(read_json(self.task/'drafts/question.json')['domain'])
        choose_domain(self.task,' 材料科学 ')
        result=begin(self.task,self.workspace)
        self.assertEqual(result['domain'],'材料科学')
        self.assertEqual(result['requires_input'],['question_type'])
        self.assertEqual(choose_type(self.task,'分析决策类')['domain'],'材料科学')
        freeze(self.task,self.candidate('材料科学'))
        self.assertTrue(begin(self.task,self.workspace)['ready'])
    def test_freeze_rejects_unconfirmed_or_mismatched_domain(self):
        choose_type(self.task,'分析决策类')
        with self.assertRaisesRegex(Error,'领域'):freeze(self.task,self.candidate('数学'))
        choose_domain(self.task,'数学')
        with self.assertRaisesRegex(Error,'领域'):freeze(self.task,self.candidate('材料科学'))
        self.assertFalse((self.task/'CURRENT.json').exists())
        for value in [None,'','   ',23]:
            with self.assertRaises(Error):choose_domain(self.task,value)
    def test_cli_records_domain_and_blocks_freeze_until_selection(self):
        from contextlib import redirect_stdout,redirect_stderr
        from io import StringIO
        from llm_authoring.cli import main
        choose_type(self.task,'分析决策类')
        file=self.task/'drafts/question.json';write_json(file,self.candidate('数学'))
        args=['--workspace',str(self.workspace),'--task',str(self.task)]
        with redirect_stdout(StringIO()),redirect_stderr(StringIO()):
            self.assertEqual(main(args+['freeze',str(file)]),2)
            self.assertEqual(main(args+['choose-domain','数学']),0)
            self.assertEqual(main(args+['freeze',str(file)]),0)
        self.assertEqual(active_question(self.task)['question']['domain'],'数学')
    def test_frozen_domain_is_kept_and_change_requires_new_question(self):
        choose_domain(self.task,'数学');choose_type(self.task,'分析决策类')
        freeze(self.task,self.candidate('数学'))
        before={p:sha(p) for p in [self.task/'REQUEST.json',self.task/'CURRENT.json',self.task/'revisions/r0001/question.json']}
        with self.assertRaisesRegex(Error,'新建题目'):choose_domain(self.task,'生物学')
        self.assertEqual(before,{p:sha(p) for p in before})
        new=Path(create_task(self.workspace,'next-question')['task'])
        self.assertIsNone(begin(new,self.workspace)['domain'])
        self.assertEqual(begin(new,self.workspace)['requires_input'],['domain','question_type'])
    def test_unfrozen_old_cs_default_is_not_treated_as_user_choice(self):
        write_json(self.task/'REQUEST.json',{'schema_version':1,'domain':'计算机科学','question_type':None,'scenario_generation':'assistant_sourced'})
        before=sha(self.task/'REQUEST.json')
        update_workspace(self.workspace)
        self.assertEqual(sha(self.task/'REQUEST.json'),before)
        self.assertIsNone(begin(self.task,self.workspace)['domain'])
        self.assertIn('domain',begin(self.task,self.workspace)['requires_input'])
    def test_legacy_frozen_task_without_explicit_domain_remains_readable(self):
        q=self.candidate('计算机科学');del q['domain']
        frozen={'question':q,'revision':'r0001','frozen_at':'2026-10-12T00:00:00+00:00',
                'question_sha256':hash_json(q),'prompt_sha256':hash_json(q['prompt']),'rubric_sha256':hash_json(q['points'])}
        write_json(self.task/'REQUEST.json',{'question_type':'分析决策类'})
        write_json(self.task/'revisions/r0001/question.json',frozen)
        write_json(self.task/'CURRENT.json',{'revision':'r0001'})
        before=sha(self.task/'revisions/r0001/question.json')
        self.assertEqual(active_question(self.task),frozen)
        result=begin(self.task,self.workspace)
        self.assertEqual(result['domain'],'计算机科学')
        self.assertNotIn('domain',result['requires_input'])
        self.assertEqual(before,sha(self.task/'revisions/r0001/question.json'))
        write_json(self.task/'REQUEST.json',{'domain':'数学','domain_confirmed':True,'question_type':'分析决策类'})
        self.assertEqual(begin(self.task,self.workspace)['domain'],'计算机科学')
        self.assertEqual(before,sha(self.task/'revisions/r0001/question.json'))
    def test_new_non_cs_question_cannot_reuse_cs_specific_review_key(self):
        from llm_authoring.authoring import self_review_template,validate_self_review
        choose_domain(self.task,'数学');choose_type(self.task,'分析决策类')
        freeze(self.task,self.candidate('数学'))
        (self.task/'drafts/sources.md').write_text('合成测试的来源说明，不能用于专业验收。')
        review=self_review_template(self.task);review['reviewer']='synthetic-domain-fixture'
        for check in review['checks'].values():check.update({'passed':True,'reason':'合成场景的逐项说明。'})
        validate_self_review(self.task,review)
        review['checks']['realistic_stable_cs_scenario']=review['checks'].pop('realistic_stable_domain_scenario')
        with self.assertRaisesRegex(Error,'旧CS自查'):validate_self_review(self.task,review)
