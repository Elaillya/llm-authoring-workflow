from pathlib import Path
import unittest
from unittest.mock import patch
from llm_authoring.core import Error,read_json,write_json,freeze_record
from llm_authoring.workspace import choose_domain,choose_type,begin
from llm_authoring.selection import choose_subdirection,menu,topic_node,domain_tree,validate_selection
import test_selection as fixtures
from test_core import question

class AvailabilityTests(unittest.TestCase):
    setUp=fixtures.SelectionTests.setUp
    tearDown=fixtures.SelectionTests.tearDown
    def catalog(self,disabled):
        import llm_authoring.selection as selection
        value=read_json(selection.CATALOG)
        def visit(nodes):
            for n in nodes:
                # This fixture exercises both states independent of shipped policy.
                if n['id']=='life_cooking_workflow':n.pop('new_questions_enabled',None)
                if n['id']==disabled:n['new_questions_enabled']=False
                visit(n.get('children',[]))
        for nodes in value['domains'].values():visit(nodes)
        p=Path(self.temp.name)/'catalog.json';write_json(p,value);return patch.object(selection,'CATALOG',p)
    def setup_branch(self):
        choose_domain(self.root,'生活娱乐')
        with self.catalog(None):choose_subdirection(self.root,'life_cooking_workflow')
        choose_type(self.root,'开放推荐类')
        q=question();q.update(task_id=read_json(self.root/'TASK.json')['task_id'],domain='生活娱乐',subdirection='life_cooking_workflow',question_type='开放推荐类');return q
    def test_inactive_leaf_hidden_but_history_and_other_children_retained(self):
        with self.catalog('life_cooking_workflow'):
            self.assertNotIn('life_cooking_workflow',{v['id'] for v in menu('生活娱乐',parent='life_daily_cooking')})
            self.assertIsNotNone(topic_node('生活娱乐','life_cooking_workflow'))
            self.assertNotIn('life_cooking_workflow',{v['id'] for v in domain_tree('生活娱乐')['topics']})
            self.assertTrue(menu('生活娱乐',parent='life_daily_cooking'))
            self.assertEqual(len(menu('计算机科学')),4)
    def test_new_choice_and_preselected_new_draft_cannot_bypass(self):
        q=self.setup_branch()
        with self.catalog('life_cooking_workflow'):
            with self.assertRaisesRegex(Error,'停止'):choose_subdirection(self.root,'life_cooking_workflow')
            with self.assertRaisesRegex(Error,'停止'):validate_selection(self.root,q)
            state=begin(self.root,self.ws)
            self.assertEqual(state['next_question']['field'],'subdirection')
            self.assertTrue(state['subdirection_choices'])
            self.assertFalse(state['can_confirm_current_scope'])
    def test_frozen_same_prompt_repair_allowed_new_prompt_rejected(self):
        q=self.setup_branch();freeze_record(self.root,q)
        with self.catalog('life_cooking_workflow'):
            self.assertTrue(begin(self.root,self.ws)['ready'])
            choose_subdirection(self.root,'life_cooking_workflow')
            validate_selection(self.root,{**q,'insight':'同一题面的考点返修'})
            with self.assertRaisesRegex(Error,'停止'):validate_selection(self.root,{**q,'prompt':q['prompt']+'新题'})
    def test_disabled_parent_hides_and_blocks_descendants(self):
        choose_domain(self.root,'生活娱乐')
        with self.catalog('life_daily_cooking'):
            self.assertEqual(menu('生活娱乐',parent='life_daily_cooking'),[])
            with self.assertRaisesRegex(Error,'停止'):choose_subdirection(self.root,'life_cooking_workflow')
