"""Synthetic end-to-end next-policy flow; no business/model quality acceptance."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
import sqlite3
import unittest
from llm_authoring.cli import main
from llm_authoring.core import Error,freeze,read_json,read_response,write_json
from llm_authoring.selection import choose_subdirection
from llm_authoring.workspace import choose_domain
from llm_authoring.references import business_context
from llm_authoring.manual import prepare_model,import_model
from llm_authoring.authoring import check_three,evaluation_template,self_review_template
from llm_authoring.ranking import export_complete,ranking_template
from llm_authoring.quality import reserve,candidate_check
from llm_authoring.memory import sync,show,context
from test_arena_ranking import fill_five
import test_diversity as diversity_fixture
from test_diversity import accept


class NextFlowTests(unittest.TestCase):
    setUp=diversity_fixture.DiversityTests.setUp
    tearDown=diversity_fixture.DiversityTests.tearDown
    candidate=diversity_fixture.DiversityTests.candidate
    def test_business_selection_review_manual_replies_to_six_md_delivery(self):
        root=self.a;choose_domain(root,'商科');choose_subdirection(root,'business_operations')
        card=business_context('business_operations')['mechanisms'][0]
        q=self.candidate(root);q.update(domain='商科',subdirection='business_operations',
              prompt='烘焙店周末排队，师傅说缺烤箱，店员说打包慢。预算只够改一处，如何先定位瓶颈再决定？',
              insight={'mechanism':card['mechanism'],'priority':'先确认约束产出的实际环节，再讨论扩容。','conclusion':'先观察并测量流程，再判断改动对象。'},
              business_mechanisms=[card['id']],business_references=[card['source_ids'][0]])
        q['author_notes']='合成结构测试，未验证专业内容与真实模型能力。'
        accept(root,q);freeze(root,q)
        def supply(role):
            file=Path(prepare_model(root,role)['input_file'])
            file.write_text('# 合成测试\n\n先核对验收依据；依据约束实现。\n');import_model(root,role)
        supply('seed');seed=evaluation_template(root,('seed',));seed['reviewer']='synthetic-test'
        for j in seed['models']['seed']['points'].values():j.update(met=False,reason='合成流程测试，非专业达成性结论。',quotes=[])
        write_json(root/'evaluations/seed-r0001.json',seed)
        for role in ('gpt','claude'):supply(role)
        ev=evaluation_template(root);ev['reviewer']='synthetic-test'
        for role,record in ev['models'].items():
            for j in record['points'].values():
                j.update(met=role!='seed',reason='合成测试逐项绑定原文字节与冻结判断，不代表模型能力。'*12,
                         quotes=['先核对验收依据'] if role!='seed' else [])
        self.assertTrue(check_three(root,ev)['three_model_gate'])
        five=fill_five(root,ev);review=self_review_template(root);review['reviewer']='synthetic-test'
        for j in review['checks'].values():j.update(passed=True,reason='合成结构检查。')
        out=root/'delivery/v001';export_complete(root,five,review,ranking_template(root,five),out)
        self.assertEqual(len(list((out/'models').glob('*.md'))),5)
        self.assertFalse((out/'screenshots').exists())
        for role,item in read_json(out/'fields.json')['models'].items():
            self.assertEqual((out/item['reply_file']).read_bytes(),(read_response(root,role)['directory']/'reply.md').read_bytes())
        self.assertEqual(context(self.b,self.ws)['other_task_entries'],1)
    def test_cli_preview_and_reservation_never_call_live_collection(self):
        from unittest.mock import patch
        q=self.candidate(self.a);write_json(self.a/'drafts/question.json',q);accept(self.a,q)
        args=['--workspace',str(self.ws),'--task',str(self.a)]
        with patch('llm_authoring.cli.collect') as network,redirect_stdout(StringIO()),redirect_stderr(StringIO()):
            self.assertEqual(main(args+['design-check',str(self.a/'drafts/question.json')]),0)
            self.assertEqual(main(args+['candidate-reserve',str(self.a/'drafts/question.json')]),0)
            self.assertEqual(main(args+['business-references','--subdirection','business_marketing']),0)
            self.assertEqual(main(args+['collect','seed','--allow-live']),2)
            network.assert_not_called()
    def test_corrupted_memory_and_symlink_database_are_rejected(self):
        q=self.candidate(self.a);accept(self.a,q);reserve(self.a,q)
        path=self.ws/'local/question-memory.sqlite3'
        with sqlite3.connect(path) as connection:connection.execute("UPDATE entries SET question_sha='tampered'")
        with self.assertRaisesRegex(Error,'绑定'):candidate_check(self.b,self.candidate(self.b,1))
        path.unlink();path.symlink_to(self.a/'drafts/sources.md')
        with self.assertRaisesRegex(Error,'符号链接'):sync(self.ws)
    def test_review_needs_specific_pass_reasons_and_semantic_comparisons(self):
        q=self.candidate(self.a);accept(self.a,q);freeze(self.a,q)
        b=self.candidate(self.b,1);review=accept(self.b,b)
        review['checks']['distinct_insight']['reason']='';write_json(self.b/'drafts/design-review.json',review)
        with self.assertRaisesRegex(Error,'具体理由'):reserve(self.b,b)
        review=accept(self.b,b);eid=review['report']['topic_index'][0]['entry_id']
        review['semantic_screen']['additional_similar_ids']=[eid]
        review['comparisons'].pop(eid,None);write_json(self.b/'drafts/design-review.json',review)
        with self.assertRaisesRegex(Error,'逐条比较'):reserve(self.b,b)
        self.assertEqual(show(self.ws,eid)['question']['task_id'],'question-001')
    def test_non_database_file_is_reported_without_a_traceback_or_reset(self):
        path=self.ws/'local/question-memory.sqlite3';path.write_bytes(b'not a SQLite database')
        error=StringIO()
        with redirect_stdout(StringIO()),redirect_stderr(error):
            result=main(['--workspace',str(self.ws),'--task',str(self.a),'status'])
        self.assertEqual(result,2);self.assertIn('本地题库',error.getvalue())
        self.assertNotIn('Traceback',error.getvalue())
        self.assertEqual(path.read_bytes(),b'not a SQLite database')
