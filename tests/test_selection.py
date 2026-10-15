"""New selection policy, with v3 frozen records kept readable."""
from pathlib import Path
import tempfile
import unittest
from llm_authoring.core import Error, read_json, write_json
from llm_authoring.workspace import begin, choose_domain, create_workspace
from llm_authoring.selection import choose_subdirection, menu, validate_selection


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.ws=Path(self.temp.name)/'ws'
        create_workspace(self.ws);self.root=self.ws/'task'
    def tearDown(self):self.temp.cleanup()
    def test_three_domains_and_cs_four_branches(self):
        result=begin(self.root,self.ws)
        self.assertEqual(result['domain_choices'],['计算机科学','商科','生活爱好类'])
        self.assertEqual(result['next_question']['field'],'domain')
        choose_domain(self.root,'计算机科学')
        result=begin(self.root,self.ws)
        self.assertEqual(result['next_question']['field'],'subdirection')
        self.assertEqual([b['id'] for b in result['subdirection_choices']],['cs_daily','cs_courses','cs_research','cs_production'])
        choose_subdirection(self.root,'cs_courses')
        self.assertEqual(begin(self.root,self.ws)['next_question']['field'],'question_type')
    def test_each_cs_branch_binds_prompt_audience(self):
        choose_domain(self.root,'计算机科学')
        for branch in menu('计算机科学'):
            value=choose_subdirection(self.root,branch['id'])
            self.assertEqual(value['subdirection'],branch['id'])
            self.assertTrue(value['guidance']['audience'])
            self.assertEqual(read_json(self.root/'REQUEST.json')['subdirection'],branch['id'])
    def test_business_seven_choices_and_no_course_detail_required(self):
        choose_domain(self.root,'商科')
        self.assertEqual(len(begin(self.root,self.ws)['subdirection_choices']),7)
        choose_subdirection(self.root,'business_operations')
        request=read_json(self.root/'REQUEST.json');request['question_type']='How-to类';write_json(self.root/'REQUEST.json',request)
        self.assertTrue(begin(self.root,self.ws)['ready'])
        validate_selection(self.root,{'domain':'商科','subdirection':'business_operations','question_type':'How-to类'})
    def test_domain_change_clears_branch_and_wrong_domain_branch_rejected(self):
        choose_domain(self.root,'计算机科学');choose_subdirection(self.root,'cs_daily')
        with self.assertRaises(Error):choose_subdirection(self.root,'business_daily')
        choose_domain(self.root,'商科')
        self.assertIsNone(read_json(self.root/'REQUEST.json')['subdirection'])
        with self.assertRaises(Error):choose_domain(self.root,'材料科学')
        with self.assertRaises(Error):validate_selection(self.root,{'domain':'商科','subdirection':'business_daily'})
    def test_legacy_request_free_domain_remains_supported(self):
        request=read_json(self.root/'REQUEST.json');request.pop('selection_schema');write_json(self.root/'REQUEST.json',request)
        choose_domain(self.root,'材料科学')
        request=read_json(self.root/'REQUEST.json');request['question_type']='How-to类';write_json(self.root/'REQUEST.json',request)
        self.assertTrue(begin(self.root,self.ws)['ready'])
