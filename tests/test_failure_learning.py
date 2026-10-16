"""Synthetic failure evidence and shared lessons, never real platform/model calls."""
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
import copy,json,unittest
import test_platform_checks as fixture
from llm_authoring import lessons
from llm_authoring import platform_checks as qa
from llm_authoring.memory import context,transaction
from llm_authoring.cli import main
from llm_authoring.core import Error,read_json

class FailureLearningTests(unittest.TestCase):
    candidate=fixture.PlatformTests.candidate
    setUp=fixture.PlatformTests.setUp
    tearDown=fixture.PlatformTests.tearDown
    fill=fixture.PlatformTests.fill
    seed=fixture.PlatformTests.seed
    three=fixture.PlatformTests.three
    frozen=fixture.PlatformTests.frozen
    run_check=fixture.PlatformTests.run_check
    def accept(self,eid):
        review=lessons.review_template(self.ws,eid)
        review.update(verdict='accepted',reviewer='synthetic-author',cause='合成题的当前表达遗漏可判定边界。',
                      prevention='新题先核对边界是否明确给出，并用同版标准统一判断。',
                      applicability='仅用于存在同类边界缺口的候选，不推断所有该领域题都失败。',
                      evidence_quotes=[review['observation']['evidence_text'][:12]])
        return lessons.review(self.ws,review)
    def test_gate_failures_are_idempotent_and_visible_to_other_tasks(self):
        self.frozen();ev=self.three()
        for role in ('gpt','claude'):
            for j in ev['models'][role]['points'].values():j.update(met=False,quotes=[])
        ids=lessons.observe_gate(self.root,ev)
        self.assertEqual(ids,lessons.observe_gate(self.root,ev));self.assertEqual(len(ids),1)
        own=lessons.failure_context(self.root,self.ws);self.assertEqual(own['observed_count'],1)
        self.assertEqual(own['accepted_lessons'],[])
        self.accept(ids[0]);shared=context(self.b,self.ws)['failure_learning']
        self.assertEqual(shared['accepted_count'],1);self.assertIn('边界',shared['accepted_lessons'][0]['prevention'])
    def test_platform_failure_waits_for_review_and_corrected_review_is_append_only(self):
        result,_=self.run_check('question',q=self.q,decision='不通过',details='题面中缺少必要约束，分析结论无法唯一验证。')
        data=lessons.failure_context(self.root,self.ws);self.assertEqual(data['pending_count'],1)
        eid=data['pending_reviews'][0]['event_id'];self.accept(eid)
        self.assertEqual(lessons.failure_context(self.b,self.ws)['accepted_count'],1)
        review=lessons.review_template(self.ws,eid);review.update(verdict='disputed',reviewer='synthetic-author',cause='复核发现题面已有约束，反馈未指出实际缺口。')
        lessons.review(self.ws,review)
        self.assertEqual(lessons.failure_context(self.b,self.ws)['accepted_count'],0)
        self.assertEqual(len(lessons.show(self.ws,eid)['reviews']),2)
    def test_cookie_service_and_unknown_results_are_not_candidate_lessons(self):
        for status in ('needs_cookie','service_error','needs_review'):
            self.assertIsNone(lessons.observe_platform(self.root,'question',{'state':status},self.q))
        self.assertEqual(lessons.failure_context(self.root,self.ws)['observed_count'],0)
    def test_early_question_without_points_can_be_remembered(self):
        early=copy.deepcopy(self.q);early.pop('points');early.pop('design_profile')
        self.run_check('question',q=early,decision='不通过',details='题目只问偏好，缺少可判定目标。')
        self.assertEqual(lessons.failure_context(self.root,self.ws)['pending_count'],1)
    def test_invalid_or_unconfirmed_evidence_does_not_become_reliable_lesson(self):
        self.run_check('question',q=self.q,decision='不通过',details='题目存在未给定的隐藏条件。')
        event=lessons.failure_context(self.root,self.ws)['pending_reviews'][0]['event_id']
        review=lessons.review_template(self.ws,event)
        with self.assertRaises(Error):lessons.review(self.ws,review)
        review.update(verdict='accepted',reviewer='test',cause='具体原因',prevention='具体改进',applicability='有限范围',evidence_quotes=['伪造原始意见'])
        with self.assertRaisesRegex(Error,'引用'):lessons.review(self.ws,review)
    def test_qa_rejects_failed_gate_without_network_but_remembers_observation(self):
        self.frozen();ev=self.three()
        for role in ('gpt','claude'):
            for j in ev['models'][role]['points'].values():j.update(met=False,quotes=[])
        with patch('llm_authoring.platform_client.call') as send:
            with self.assertRaises(Error):qa.run_models(self.root,ev)
            send.assert_not_called()
        self.assertEqual(lessons.failure_context(self.b,self.ws)['observed_count'],1)
    def test_seed_cli_records_failure_but_validation_function_keeps_its_read_only_contract(self):
        from llm_authoring.authoring import check_seed
        self.frozen();ev=self.seed(met=True)
        check_seed(self.root,ev)
        self.assertEqual(lessons.failure_context(self.root,self.ws)['observed_count'],0)
        output=StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['--task',str(self.root),'seed-check',str(self.root/'evaluations/seed-r0001.json')]),0)
        self.assertEqual(lessons.failure_context(self.b,self.ws)['observed_count'],1)
    def test_disagreement_with_evidence_removes_previously_accepted_lesson(self):
        # Use the existing fixture's proven feedback/input disagreement path.
        ev,decision=fixture.PlatformTests.disputed(self)
        data=lessons.failure_context(self.root,self.ws);eid=data['pending_reviews'][0]['event_id']
        self.accept(eid);qa.disagree(self.root,decision,ev)
        self.assertEqual(lessons.failure_context(self.b,self.ws)['accepted_count'],0)
        self.assertEqual(lessons.show(self.ws,eid)['reviews'][-1]['verdict'],'disputed')
    def test_other_parent_is_isolated_and_lesson_changes_do_not_change_duplicate_snapshot(self):
        from llm_authoring.workspace import create_workspace
        from llm_authoring.memory import snapshot,records
        other=self.ws.parent/'other';create_workspace(other)
        self.run_check('question',q=self.q,decision='不通过',details='隐藏前提未明确，题目不稳定。')
        eid=lessons.failure_context(self.root,self.ws)['pending_reviews'][0]['event_id']
        with transaction(self.ws) as db:before=snapshot(records(db),'another')
        self.accept(eid)
        with transaction(self.ws) as db:self.assertEqual(before,snapshot(records(db),'another'))
        self.assertEqual(lessons.failure_context(other/'task',other)['observed_count'],0)
