import json
from pathlib import Path
import tempfile
import unittest
from llm_authoring.core import Error,ROLES,read_response,sha,write_json
from llm_authoring.authoring import export_authoring,self_review_template
from test_core import prepared,populate


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);prepared(self.root);self.ev=populate(self.root)
        from PIL import Image
        for role in ROLES:
            item=read_response(self.root,role);d=item['directory'];m=item['meta']
            # Synthetic structural image only. Browser rendering has a separate integration test.
            Image.new('RGB',(640,480),'white').save(d/'reply.png')
            m.update({'screenshot':'reply.png','screenshot_kind':'api_rendered','screenshot_sha256':sha(d/'reply.png'),'evidence_status':'verified',
                      'model_identity_check':'returned_model_matches_configured_id_allowing_punctuation'})
            write_json(d/'metadata.json',m)
            write_json(d/'render-manifest.json',{'full_page':True,'reply_sha256':m['reply_sha256'],'png_sha256':m['screenshot_sha256']})
        self.review=self_review_template(self.root);self.review['reviewer']='synthetic-self-review'
        for check in self.review['checks'].values():check.update({'passed':True,'reason':'合成夹具，仅验证字段和版本约束。'})
    def tearDown(self):self.tmp.cleanup()
    def test_three_model_export_has_all_authoring_fields_and_no_ranking(self):
        output=self.root/'delivery';export_authoring(self.root,self.ev,self.review,output)
        fields=json.loads((output/'fields.json').read_text());self.assertEqual(fields['supporting_points'],'无')
        self.assertEqual(len(fields['models']),3);self.assertNotIn('ranking',fields)
        for role in ROLES:self.assertEqual((output/'models'/f'{role}.md').read_bytes(),(read_response(self.root,role)['directory']/'reply.md').read_bytes())
        self.assertEqual(len(list((output/'screenshots').glob('*.png'))),3)
        handoff=json.loads((output/'handoff.json').read_text());self.assertEqual(handoff['models_in_order'],list(ROLES));self.assertEqual(handoff['next_workflow'],'arena_and_ranking')
        manifest=json.loads((output/'manifest.json').read_text())
        for filename,digest in manifest['files'].items():self.assertEqual(sha(output/filename),digest)
    def test_no_export_when_three_model_gate_fails(self):
        for point in self.ev['models']['seed']['points'].values():point.update({'met':True,'quotes':['先核对验收依据']})
        with self.assertRaisesRegex(Error,'区分度'):export_authoring(self.root,self.ev,self.review,self.root/'out')
        self.assertFalse((self.root/'out').exists())
    def test_changed_screenshot_or_api_raw_prevents_delivery(self):
        item=read_response(self.root,'seed');(item['directory']/'reply.png').write_bytes(b'damaged')
        with self.assertRaisesRegex(Error,'截图'):export_authoring(self.root,self.ev,self.review,self.root/'out')
    def test_self_review_must_match_question_and_specific_type(self):
        self.review['question_sha256']='obsolete'
        with self.assertRaisesRegex(Error,'自查版本'):export_authoring(self.root,self.ev,self.review,self.root/'out')
    def test_incomplete_point_is_not_a_negative_model_result(self):
        self.ev['models']['seed']['points']['D1']['met']=None
        with self.assertRaisesRegex(Error,'证据不足'):export_authoring(self.root,self.ev,self.review,self.root/'out')
    def test_changed_source_notes_require_updated_self_review(self):
        (self.root/'drafts/sources.md').write_text('修订的专业依据笔记。')
        with self.assertRaisesRegex(Error,'专业依据'):export_authoring(self.root,self.ev,self.review,self.root/'out')
