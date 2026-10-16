"""Hierarchical life-topic choice without altering established CS/business choices."""
from contextlib import redirect_stdout
from io import StringIO
import json,unittest
from llm_authoring.cli import main
from llm_authoring.core import Error,read_json
from llm_authoring.workspace import begin,choose_domain,choose_type
from llm_authoring.selection import choose_subdirection,menu,topic_index,topic_node,validate_selection
import test_selection as fixtures


class LifestyleSelectionTests(unittest.TestCase):
    setUp=fixtures.SelectionTests.setUp
    tearDown=fixtures.SelectionTests.tearDown

    def test_three_domains_and_five_life_roots(self):
        self.assertEqual(menu(),['计算机科学','商科','生活娱乐'])
        choose_domain(self.root,'生活娱乐')
        state=begin(self.root,self.ws)
        self.assertEqual(len(state['subdirection_choices']),5)
        self.assertTrue(all('children' not in item for item in state['subdirection_choices']))
        self.assertEqual(state['next_question']['field'],'subdirection')

    def test_rock_path_can_be_selected_level_by_level(self):
        choose_domain(self.root,'生活娱乐')
        for node in ('life_hobbies','life_arts','life_arts_music'):
            choose_subdirection(self.root,node)
            state=begin(self.root,self.ws)
            self.assertEqual(state['next_question']['field'],'subdirection')
            self.assertEqual(state['selection_path'][-1]['id'],node)
            self.assertTrue(state['can_confirm_current_scope'])
        choose_subdirection(self.root,'life_music_rock')
        state=begin(self.root,self.ws)
        self.assertEqual(state['next_question']['field'],'question_type')
        self.assertEqual([item['label'] for item in state['selection_path']],['兴趣爱好','文艺与审美','音乐','摇滚与乐队'])

    def test_explicit_leaf_can_be_chosen_directly(self):
        choose_domain(self.root,'生活娱乐');choose_subdirection(self.root,'life_ball_table_tennis')
        path=read_json(self.root/'REQUEST.json')['subdirection_path']
        self.assertEqual(path[-1],'life_ball_table_tennis');self.assertGreaterEqual(len(path),4)
        choose_type(self.root,'How-to类');self.assertTrue(begin(self.root,self.ws)['ready'])

    def test_user_can_stop_at_a_useful_internal_scope(self):
        choose_domain(self.root,'生活娱乐');choose_subdirection(self.root,'life_arts_music')
        choose_type(self.root,'分析决策类')
        q={'domain':'生活娱乐','subdirection':'life_arts_music','question_type':'分析决策类'}
        with self.assertRaisesRegex(Error,'确认|细分'):validate_selection(self.root,q)
        choose_subdirection(self.root,'life_arts_music',confirm=True)
        self.assertTrue(begin(self.root,self.ws)['ready']);validate_selection(self.root,q)

    def test_confirmed_scope_is_idempotent_but_new_scope_needs_confirmation(self):
        choose_domain(self.root,'生活娱乐')
        choose_subdirection(self.root,'life_arts_music',confirm=True)
        choose_subdirection(self.root,'life_arts_music')
        self.assertEqual(begin(self.root,self.ws)['next_question']['field'],'question_type')
        choose_subdirection(self.root,'life_arts_visual')
        self.assertEqual(begin(self.root,self.ws)['next_question']['field'],'subdirection')

    def test_changing_domain_clears_all_path_state(self):
        choose_domain(self.root,'生活娱乐');choose_subdirection(self.root,'life_music_rock')
        choose_domain(self.root,'商科');request=read_json(self.root/'REQUEST.json')
        self.assertIsNone(request['subdirection']);self.assertFalse(request.get('subdirection_confirmed',False))
        self.assertEqual(request.get('subdirection_path',[]),[])
        with self.assertRaises(Error):choose_subdirection(self.root,'life_music_rock')
        self.assertEqual(len(menu('商科')),7);self.assertEqual(len(menu('计算机科学')),4)

    def test_tree_ids_paths_and_menu_children_are_consistent(self):
        index=topic_index('生活娱乐')
        self.assertGreater(len(index),60)
        self.assertEqual(len({item['id'] for item in index}),len(index))
        for node in index:
            self.assertEqual(node['path_ids'][-1],node['id']);self.assertTrue(node['audience']);self.assertTrue(node['guidance'])
        parent=topic_node('生活娱乐','life_sports_racket')
        self.assertIn('life_ball_table_tennis',{item['id'] for item in menu('生活娱乐',parent=parent['id'])})
        self.assertEqual(menu('生活娱乐',parent='unknown'),[])

    def test_cli_tree_and_confirm_do_not_make_model_or_platform_calls(self):
        from unittest.mock import patch
        args=['--workspace',str(self.ws),'--task',str(self.root)]
        choose_domain(self.root,'生活娱乐')
        with patch('llm_authoring.platform_client.call') as platform,patch('llm_authoring.cli.collect') as model:
            with redirect_stdout(StringIO()):
                self.assertEqual(main(args+['choose-subdirection','life_arts_music','--confirm']),0)
            output=StringIO()
            with redirect_stdout(output):self.assertEqual(main(args+['domain-tree','--domain','生活娱乐']),0)
            data=json.loads(output.getvalue());self.assertGreater(data['nodes'],60)
            platform.assert_not_called();model.assert_not_called()
