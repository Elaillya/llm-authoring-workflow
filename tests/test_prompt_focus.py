"""Synthetic prompt style and frozen-contract regression checks; no live calls."""
from pathlib import Path
from unittest.mock import patch
import copy
import unittest
from llm_authoring.core import Error,active_question,freeze,freeze_record,sha,write_json
from llm_authoring.prompt_style import focus_signals,validate_new_prompt
from llm_authoring.quality import candidate_check,reserve,review_template
from llm_authoring import platform_checks as qa
import test_diversity as diversity


class PromptFocusTests(unittest.TestCase):
    setUp=diversity.DiversityTests.setUp
    tearDown=diversity.DiversityTests.tearDown
    candidate=diversity.DiversityTests.candidate

    def test_split_questions_and_standalone_reason_requests_are_detected(self):
        for prompt in ('该先定位电路问题还是换灯？用什么工具？','换哪款台灯，为什么？',
                       '该换台灯吗；为何？','用哪款台灯，理由是什么？','选哪款台灯，请说明理由。'):
            with self.subTest(prompt=prompt):self.assertTrue(focus_signals(prompt))

    def test_single_causal_or_integrated_task_and_data_question_marks_are_allowed(self):
        for prompt in ('为什么换了灯泡还是闪烁？','怎样依据使用条件选择适合书桌的台灯？',
                       '怎样安排两项工作才能兼顾理解和效率？',
                       '示例接口https://example.test/api?q=lamp 如何检查参数？',
                       '代码中的`?`与`??`该如何区分？'):
            with self.subTest(prompt=prompt):self.assertEqual(focus_signals(prompt),[])

    def test_bad_new_question_stops_before_configuration_and_network(self):
        q=self.candidate(self.a);q['prompt']='台灯怎么选，为什么？'
        with patch('llm_authoring.platform_client.configuration') as config,patch('llm_authoring.platform_client.call') as send:
            with self.assertRaisesRegex(Error,'一个核心问题'):qa.run(self.a,'question',q=q)
            config.assert_not_called();send.assert_not_called()
        self.assertFalse(list((self.a/'platform-checks').glob('question-*')))

    def test_bad_new_prompt_cannot_be_designed_reserved_or_frozen(self):
        q=self.candidate(self.a);q['prompt']='先定位还是先换灯？用什么工具？'
        for operation in (candidate_check,reserve,freeze):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(Error,'一个核心问题'):operation(self.a,q)
        self.assertFalse((self.a/'CURRENT.json').exists())

    def test_single_mark_still_requires_explicit_semantic_review(self):
        q=self.candidate(self.a);q['prompt']='怎样安排两项工作才能兼顾理解和效率？'
        review=diversity.accept(self.a,q)
        self.assertIn('single_core_question',review_template(self.a,q)['checks'])
        review['checks'].pop('single_core_question');write_json(self.a/'drafts/design-review.json',review)
        with self.assertRaisesRegex(Error,'单一核心问题'):reserve(self.a,q)
        review=diversity.accept(self.a,q);review['checks']['single_core_question']['passed']=False
        write_json(self.a/'drafts/design-review.json',review)
        with self.assertRaisesRegex(Error,'设计复核未通过'):reserve(self.a,q)

    def test_frozen_split_prompt_remains_readable_without_rewriting_evidence(self):
        q=self.candidate(self.a);q['prompt']='先定位还是先换灯？用什么工具？'
        # Construct a pre-upgrade frozen fixture, never a new accepted design.
        old=freeze_record(self.a,q)
        files=[self.a/'CURRENT.json',self.a/'revisions/r0001/question.json']
        before={p:sha(p) for p in files}
        self.assertEqual(active_question(self.a),old)
        validate_new_prompt(self.a,q['prompt']);qa.initial_question(self.a,q)
        self.assertEqual(freeze(self.a,q),old)
        repaired=copy.deepcopy(q);repaired['insight']['mechanism']+='合成考点修复。'
        diversity.accept(self.a,repaired)
        self.assertEqual(freeze(self.a,repaired)['revision'],'r0002')
        self.assertEqual(sha(files[1]),before[files[1]])
        with self.assertRaisesRegex(Error,'一个核心问题'):
            validate_new_prompt(self.a,'先换开关？还是先检修？')
