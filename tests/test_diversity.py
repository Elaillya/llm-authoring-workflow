"""Private synthetic question memory and pre-freeze design review."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import copy
import tempfile
import unittest
from llm_authoring.core import Error, freeze, read_json, sha, write_json
from llm_authoring.workspace import choose_domain, choose_type, create_task, create_workspace
from llm_authoring.selection import choose_subdirection
from llm_authoring.quality import candidate_check, review_template, reserve, naturalness_signals
from llm_authoring.memory import context, records, sync, transaction, remember
from test_core import question


def accept(root,q):
    review=review_template(root,q);review['reviewer']='synthetic-author'
    review['semantic_screen']={'screened_entry_ids':[i['entry_id'] for i in review['report']['topic_index']],
                              'additional_similar_ids':[],'reason':'合成测试逐条核对场景、机制和评分目标。'}
    for c in review['checks'].values():c.update(passed=True,reason='合成测试逐项核对，未作为真实题或专业验收。')
    for c in review['comparisons'].values():c.update(decision='distinct',reason='合成场景的目标与判断机制不同，按实际内容比较。',difference_axes=['goal','mechanism'])
    write_json(root/'drafts/design-review.json',review)
    return review


class DiversityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.ws=Path(self.temp.name)/'ws';create_workspace(self.ws)
        self.a=self.ws/'question-001';self.b=Path(create_task(self.ws,'second')['task'])
        for root in (self.a,self.b):
            # Exercise the earlier diversity contract independently of new QA gates.
            task=read_json(root/'TASK.json');task.pop('platform_checks_required',None);write_json(root/'TASK.json',task)
            choose_domain(root,'计算机科学');choose_subdirection(root,'cs_courses');choose_type(root,'分析决策类')
            (root/'drafts/sources.md').write_text('合成测试的专业依据说明，未开展真实专业实验。')
    def tearDown(self):self.temp.cleanup()
    def candidate(self,root,variant=0):
        q=question();q.update(task_id=read_json(root/'TASK.json')['task_id'],subdirection='cs_courses')
        q['prompt']='课程项目要先核对验收依据，还是先批量生成代码？' if variant==0 else '排序实验只有一半样例通过，我该先查边界条件还是继续微调常数？'
        q['insight']={'mechanism':'验收依据约束实现范围并形成可验证目标。' if variant==0 else '边界条件决定算法在空输入与重复数据上的正确性。',
                      'priority':'先识别任务边界，才能判断代码是否解决实际需求。' if variant==0 else '首先保证输入边界上的正确性，再评估常数优化。',
                      'conclusion':'先核对验收依据，再进行实现并检查。' if variant==0 else '先用边界输入定位逻辑问题，再改善运行速度。'}
        q['points']=[{'id':'D1','kind':'decisive','criterion':'依据验收目标解释为何先明确范围再实现代码。' if variant==0 else '利用边界输入反例确定排序逻辑错误，先保证正确性。'}]
        q['design_profile']={'scenario':'课程项目开发' if variant==0 else '排序课程实验','goal':'确定实现范围' if variant==0 else '修复算法边界错误',
             'constraints':['已有验收要求'] if variant==0 else ['只有部分样例通过'],
             'mechanism_tags':['验收约束实现范围'] if variant==0 else ['输入边界决定正确性'],
             'point_targets':['需求与验收一致'] if variant==0 else ['用边界反例定位错误'],
             'reasoning_path':['验收','范围','实现'] if variant==0 else ['反例','逻辑修复','性能']}
        return q
    def test_freeze_requires_design_review_then_remembers_question(self):
        q=self.candidate(self.a)
        with self.assertRaises(Error):freeze(self.a,q)
        self.assertFalse((self.a/'CURRENT.json').exists())
        accept(self.a,q);freeze(self.a,q)
        c=context(self.b,self.ws)
        self.assertEqual(c['other_task_entries'],1)
        self.assertEqual(c['recent_questions'][0]['question']['prompt'],q['prompt'])
        self.assertTrue((self.ws/'local/question-memory.sqlite3').is_file())
    def test_duplicate_prompt_insight_and_points_are_each_detected(self):
        original=self.candidate(self.a);accept(self.a,original);freeze(self.a,original)
        q=self.candidate(self.b,1)
        for field in ('prompt','insight','points'):
            changed=copy.deepcopy(q);changed[field]=copy.deepcopy(original[field])
            report=candidate_check(self.b,changed)
            self.assertTrue(report['hard_duplicates'],field)
            accept(self.b,changed)
            with self.assertRaisesRegex(Error,'重复'):reserve(self.b,changed)
    def test_profile_recalls_paraphrases_without_external_model(self):
        q=self.candidate(self.a);accept(self.a,q);freeze(self.a,q)
        other=self.candidate(self.b,1);other['design_profile']=copy.deepcopy(q['design_profile'])
        report=candidate_check(self.b,other)
        self.assertEqual(report['neighbors'][0]['scores']['profile'],1.0)
        self.assertEqual(report['neighbors'][0]['risk'],'high')
    def test_schema_labels_and_generic_verbs_do_not_make_distinct_topics_duplicates(self):
        q=self.candidate(self.a);accept(self.a,q);freeze(self.a,q)
        other=self.candidate(self.b,1)
        self.assertFalse(candidate_check(self.b,other)['hard_duplicates'])
        accept(self.b,other);freeze(self.b,other)
    def test_same_task_revision_reuses_own_history(self):
        q=self.candidate(self.a);accept(self.a,q);freeze(self.a,q)
        q['insight']['conclusion']+='补充适用边界。';accept(self.a,q)
        self.assertEqual(freeze(self.a,q)['revision'],'r0002')
        self.assertEqual(context(self.b,self.ws)['other_task_entries'],2)
    def test_stale_memory_or_source_notes_blocks_freeze(self):
        a=self.candidate(self.a);b=self.candidate(self.b,1);accept(self.b,b)
        accept(self.a,a);freeze(self.a,a)
        with self.assertRaisesRegex(Error,'复核.*过期'):freeze(self.b,b)
        accept(self.b,b);(self.b/'drafts/sources.md').write_text('新的来源笔记。')
        with self.assertRaisesRegex(Error,'复核.*过期'):freeze(self.b,b)
        self.assertFalse((self.b/'CURRENT.json').exists())
    def test_naturalness_is_a_signal_and_does_not_forbid_research_terms(self):
        q=self.candidate(self.a);q['prompt']='请从技术、管理和文化三个维度构建可落地、可量化、可复制的闭环方案。'
        self.assertTrue(naturalness_signals(q))
        choose_subdirection(self.a,'cs_research');q['subdirection']='cs_research';q['prompt']='Agent复现实验中工具返回不同，如何控制随机性并保留可比的轨迹？'
        self.assertFalse(naturalness_signals(q))
        accept(self.a,q);freeze(self.a,q)
    def test_two_simultaneous_reservations_cannot_both_pass_stale_review(self):
        a=self.candidate(self.a);b=self.candidate(self.b,1);accept(self.a,a);accept(self.b,b)
        def call(root,q):
            try:reserve(root,q);return 'ok'
            except Error:return 'stale'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda item:call(*item),[(self.a,a),(self.b,b)]))
        self.assertEqual(sorted(results),['ok','stale'])
    def test_legacy_sync_preserves_originals_and_is_idempotent(self):
        request=read_json(self.a/'REQUEST.json');request.pop('selection_schema');write_json(self.a/'REQUEST.json',request)
        q=question();q['task_id']='question-001';freeze(self.a,q)
        protected={p:sha(p) for p in [self.a/'CURRENT.json',self.a/'revisions/r0001/question.json',self.a/'TASK.json']}
        result=sync(self.ws);self.assertEqual(result['imported'],1)
        self.assertEqual(sync(self.ws)['imported'],0)
        self.assertEqual(protected,{p:sha(p) for p in protected})
    def test_rejected_candidates_are_remembered_without_global_memory(self):
        q=self.candidate(self.a)
        with transaction(self.ws) as db:remember(db,self.a,q,'rejected',note='合成候选缺乏区分度。')
        self.assertEqual(context(self.b,self.ws)['recent_questions'][0]['status'],'rejected')
        self.assertTrue(candidate_check(self.b,{**q,'task_id':'second'})['hard_duplicates'])
    def test_freeze_is_idempotent_without_rewriting_review_or_memory(self):
        q=self.candidate(self.a);accept(self.a,q);first=freeze(self.a,q)
        before=sha(self.ws/'local/question-memory.sqlite3')
        other=self.candidate(self.b,1);accept(self.b,other);freeze(self.b,other)
        before=sha(self.ws/'local/question-memory.sqlite3')
        self.assertEqual(freeze(self.a,q),first)
        self.assertEqual(sha(self.ws/'local/question-memory.sqlite3'),before)
    def test_all_memory_index_must_be_screened_even_when_not_lexically_similar(self):
        q=self.candidate(self.a);accept(self.a,q);freeze(self.a,q)
        other=self.candidate(self.b,1);review=accept(self.b,other)
        review['semantic_screen']['screened_entry_ids']=[]
        write_json(self.b/'drafts/design-review.json',review)
        with self.assertRaisesRegex(Error,'全库机制索引'):reserve(self.b,other)
    def test_reservation_requires_confirmed_domain_and_matching_selected_type(self):
        q=self.candidate(self.a);accept(self.a,q)
        original=read_json(self.a/'REQUEST.json')
        for changes in ({'domain_confirmed':False},{'domain':'商科'},
                        {'question_type':None},{'question_type':'How-to类'}):
            write_json(self.a/'REQUEST.json',{**original,**changes})
            with self.assertRaisesRegex(Error,'先询问'):reserve(self.a,q)
            with transaction(self.ws) as db:self.assertEqual(records(db),[])
        write_json(self.a/'REQUEST.json',original);reserve(self.a,q)
    def test_all_high_risk_matches_require_comparison_even_after_eighth(self):
        q=self.candidate(self.b,1)
        # Distinct original texts, but the same mechanism/point profile. The
        # ninth recalled candidate must not disappear behind a display limit.
        for letter in 'ABCDEFGHI':
            other=Path(create_task(self.ws,'prior-'+letter)['task'])
            prior=copy.deepcopy(q);prior['task_id']='prior-'+letter
            prior['prompt']='合成案例'+letter+'的处理对象与目标是什么？'
            prior['insight']={key:'合成案例'+letter+'的'+key+'依据。' for key in q['insight']}
            prior['points']=[{'id':'D1','kind':'decisive','criterion':'合成案例'+letter+'的单独评分要求。'}]
            with transaction(self.ws) as db:remember(db,other,prior,'rejected',note='合成测试候选。')
        review=accept(self.b,q)
        self.assertEqual(len(review['report']['neighbors']),9)
        self.assertTrue(all(n['risk']=='high' for n in review['report']['neighbors']))
        review['comparisons'].pop(review['report']['neighbors'][-1]['entry_id'])
        write_json(self.b/'drafts/design-review.json',review)
        with self.assertRaisesRegex(Error,'逐条比较'):reserve(self.b,q)
    def test_freeze_file_failure_leaves_no_partial_revision_to_block_siblings(self):
        from unittest.mock import patch
        q=self.candidate(self.a);accept(self.a,q)
        original=write_json
        def fail_question(path,value):
            if Path(path).name=='question.json':raise OSError('synthetic disk failure')
            return original(path,value)
        with patch('llm_authoring.core.write_json',side_effect=fail_question):
            with self.assertRaises(OSError):freeze(self.a,q)
        self.assertFalse((self.a/'CURRENT.json').exists())
        self.assertEqual(list((self.a/'revisions').iterdir()),[])
        candidate_check(self.b,self.candidate(self.b,1))
    def test_current_pointer_failure_preserves_complete_readable_revision(self):
        from unittest.mock import patch
        q=self.candidate(self.a);accept(self.a,q)
        original=write_json
        def fail_current(path,value):
            if Path(path).name=='CURRENT.json':raise OSError('synthetic pointer failure')
            return original(path,value)
        with patch('llm_authoring.core.write_json',side_effect=fail_current):
            with self.assertRaises(OSError):freeze(self.a,q)
        self.assertFalse((self.a/'CURRENT.json').exists())
        self.assertTrue((self.a/'revisions/r0001/question.json').is_file())
        report=candidate_check(self.b,self.candidate(self.b,1))
        self.assertEqual(len(report['topic_index']),1)
    def test_repeated_reservation_does_not_downgrade_frozen_or_delivered_entry(self):
        q=self.candidate(self.a);accept(self.a,q);freeze(self.a,q)
        self.assertEqual(reserve(self.a,q)['status'],'frozen')
        with transaction(self.ws) as db:remember(db,self.a,q,'delivered','r0001')
        self.assertEqual(reserve(self.a,q)['status'],'delivered')
        self.assertEqual(context(self.b,self.ws)['recent_questions'][0]['status'],'delivered')
