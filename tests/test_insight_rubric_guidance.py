"""Synthetic integration checks for mandatory research and frozen evidence."""
from pathlib import Path
import copy
import unittest
from llm_authoring.core import Error,active_question,freeze,freeze_record,sha,write_json
from llm_authoring.quality import candidate_check,reserve,review_template
from llm_authoring.workspace import begin,create_task
import test_diversity as diversity


class InsightRubricGuidanceTests(unittest.TestCase):
    setUp=diversity.DiversityTests.setUp
    tearDown=diversity.DiversityTests.tearDown
    candidate=diversity.DiversityTests.candidate

    def test_portable_materials_are_available_at_start_design_and_in_new_task(self):
        q=self.candidate(self.a)
        refs=begin(self.a,self.ws)['authoring_references']
        self.assertEqual(candidate_check(self.a,q)['required_references'],refs)
        self.assertEqual(refs['design_review_check'],'insight_rubric_alignment')
        for name in ('research_report','checklist'):
            source=Path(refs[name]);self.assertTrue(source.is_file())
            copied=self.a/'.agents/skills/llm-authoring-workflow/references'/source.name
            self.assertEqual(copied.read_bytes(),source.read_bytes())
            self.assertNotIn('/srv/',source.read_text())
        extra=Path(create_task(self.ws,'new-portable')['task'])
        for name in ('research_report','checklist'):
            source=Path(refs[name]);self.assertEqual((extra/'.agents/skills/llm-authoring-workflow/references'/source.name).read_bytes(),source.read_bytes())

    def test_new_candidate_requires_alignment_review_with_a_pass_and_reason(self):
        q=self.candidate(self.a)
        review=diversity.accept(self.a,q)
        self.assertIn('insight_rubric_alignment',review_template(self.a,q)['checks'])
        review['checks'].pop('insight_rubric_alignment');write_json(self.a/'drafts/design-review.json',review)
        with self.assertRaisesRegex(Error,'insight_rubric_alignment'):reserve(self.a,q)
        for passed,reason in ((False,'needs repair'),(True,'')):
            review=diversity.accept(self.a,q);review['checks']['insight_rubric_alignment']={'passed':passed,'reason':reason}
            write_json(self.a/'drafts/design-review.json',review)
            with self.assertRaisesRegex(Error,'设计复核未通过'):freeze(self.a,q)
        self.assertFalse((self.a/'CURRENT.json').exists())
        diversity.accept(self.a,q);self.assertEqual(freeze(self.a,q)['revision'],'r0001')

    def test_existing_frozen_question_remains_idempotent_without_new_review(self):
        q=self.candidate(self.a);old=freeze_record(self.a,q)
        protected=[self.a/'CURRENT.json',self.a/'revisions/r0001/question.json']
        before={p:sha(p) for p in protected}
        self.assertEqual(active_question(self.a),old)
        self.assertEqual(freeze(self.a,q),old)
        self.assertEqual(before,{p:sha(p) for p in protected})
        repaired=copy.deepcopy(q);repaired['insight']['mechanism']+='合成修复补充核心对应。'
        review=diversity.accept(self.a,repaired);review['checks'].pop('insight_rubric_alignment')
        write_json(self.a/'drafts/design-review.json',review)
        with self.assertRaisesRegex(Error,'insight_rubric_alignment'):freeze(self.a,repaired)
        diversity.accept(self.a,repaired);self.assertEqual(freeze(self.a,repaired)['revision'],'r0002')
        self.assertEqual(sha(protected[1]),before[protected[1]])
