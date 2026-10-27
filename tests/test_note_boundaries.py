"""Author-note formatting at real export entry points; originals remain verbatim."""
import copy
import unittest
from unittest.mock import patch
from llm_authoring.delivery import attainment_notes,join_note_fields
from llm_authoring.ranking import ranking_template
from llm_authoring.core import ALL_ROLES
import test_export as export_fixtures
from llm_authoring.authoring import export_authoring


class NoteBoundaryTests(unittest.TestCase):
    def test_endings_and_quotes_keep_sentence_and_evidence_contents(self):
        quote='原话。；代码 x = "。；"'
        for reason in ['判断正确','判断正确。','判断正确；','判断正确。\n','判断正确！','判断正确.','说明“判断正确。”']:
            stat={'judgments':[{'id':'D1','kind':'decisive','met':True,'reason':reason,'quotes':[quote]}]}
            before=copy.deepcopy(stat)
            text=attainment_notes(stat)
            boundary=text.split('原文依据：')[0]
            self.assertNotIn('。；',boundary);self.assertNotIn('；；',boundary);self.assertNotIn('.；',boundary)
            self.assertTrue(text.endswith(quote));self.assertEqual(stat,before)
            self.assertNotIn('原文依据：',attainment_notes({'judgments':[{**stat['judgments'][0],'quotes':[]}]}))

    def test_ranking_joins_point_reasons_without_double_punctuation(self):
        stat={'attained':True,'decisive_met':2,'decisive_total':2,'total_met':2,'total_points':2,
              'judgments':[{'id':'D1','met':True,'reason':'结论正确。'},{'id':'D2','met':True,'reason':'理由正确。'}]}
        result={'models':{role:stat for role in ALL_ROLES},'order':'synthetic','groups':[list(ALL_ROLES)]}
        for role in ALL_ROLES:result['models'][role]={**stat,'name':role}
        with patch('llm_authoring.ranking.active_question',return_value={'question':{'task_id':'test'},'question_sha256':'test'}),patch('llm_authoring.ranking.check_five',return_value=result):
            notes=ranking_template('.',{'reviewer':'synthetic'})['models']
        self.assertTrue(all('。；' not in value for value in notes.values()))


class ExportNoteBoundaryTests(unittest.TestCase):
    setUp=export_fixtures.ExportTests.setUp
    tearDown=export_fixtures.ExportTests.tearDown
    def test_checkpoint_uses_same_formatter_without_mutating_evaluation(self):
        for model in self.ev['models'].values():
            for point in model['points'].values():point['reason']='合成判断正确。'
        before=copy.deepcopy(self.ev)
        output=self.root/'notes-export';export_authoring(self.root,self.ev,self.review,output)
        import json
        fields=json.loads((output/'fields.json').read_text(encoding='utf-8'))
        self.assertTrue(all('。；' not in item['attainment_notes'] for item in fields['models'].values()))
        self.assertEqual(self.ev,before)
