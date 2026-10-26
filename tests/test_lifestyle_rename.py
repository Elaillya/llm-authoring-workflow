"""A display rename must keep legacy selection, payload and frozen evidence valid."""
from pathlib import Path
import unittest
from llm_authoring.selection import menu,domain_tree,choose_subdirection,topic_index,new_question_available
from llm_authoring.workspace import begin,choose_domain
from llm_authoring.references import lifestyle_library,validate_lifestyle_references
from llm_authoring.core import Error,freeze,read_json,write_json,active_question
from llm_authoring import platform_checks as qa
import test_platform_checks as fixture
import test_diversity as diversity

class LifestyleRenameTests(unittest.TestCase):
    setUp=fixture.PlatformTests.setUp
    tearDown=fixture.PlatformTests.tearDown
    candidate=fixture.PlatformTests.candidate
    run_check=fixture.PlatformTests.run_check
    def test_aliases_select_new_display_without_duplicate_menu_entries(self):
        self.assertEqual(menu(),['计算机科学','商科','生活娱乐'])
        for name in ('生活爱好','生活爱好类','生活娱乐类','生活娱乐'):
            self.assertEqual(choose_domain(self.root,name)['domain'],'生活娱乐')
            self.assertEqual(domain_tree(name)['domain'],'生活娱乐')
            self.assertEqual(len(topic_index(name)),92)  # historical IDs retained
            self.assertEqual(domain_tree(name)['nodes'],sum(new_question_available(name,n['id']) for n in topic_index(name)))
            self.assertEqual(domain_tree(name)['topics'],domain_tree('生活娱乐')['topics'])
    def test_old_frozen_label_and_cached_platform_payload_are_preserved(self):
        choose_domain(self.root,'生活娱乐');choose_subdirection(self.root,'life_garden_indoor')
        card=next(c for c in lifestyle_library()['mechanisms'] if c['id']=='LH-C-M01')
        req=read_json(self.root/'REQUEST.json');req['domain']='生活爱好类';write_json(self.root/'REQUEST.json',req)
        self.q.update(domain='生活爱好类',subdirection='life_garden_indoor',lifestyle_mechanisms=[card['id']],
                      lifestyle_references=card['source_ids'],insight=card['decisive_factor'])
        result,send=self.run_check('question',q=self.q)
        self.assertEqual(send.call_args.args[1]['params']['领域'],'生活爱好')
        diversity.accept(self.root,self.q);freeze(self.root,self.q)
        original=(self.root/'revisions/r0001/question.json').read_bytes();request=(self.root/'REQUEST.json').read_bytes()
        self.assertEqual(begin(self.root,self.ws)['domain'],'生活娱乐')
        self.assertTrue(qa.question_gate(self.root,active_question(self.root)['question'])['accepted'])
        cached,send=self.run_check('question',q=self.q);self.assertTrue(cached['cached']);send.assert_not_called()
        self.assertEqual((self.root/'revisions/r0001/question.json').read_bytes(),original)
        self.assertEqual((self.root/'REQUEST.json').read_bytes(),request)
    def test_old_name_still_requires_lifestyle_reference_binding(self):
        q={'domain':'生活爱好类','lifestyle_mechanisms':[],'lifestyle_references':[]}
        with self.assertRaisesRegex(Error,'机制卡'):validate_lifestyle_references(self.root,q)
