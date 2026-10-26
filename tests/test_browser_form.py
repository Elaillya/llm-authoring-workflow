"""Synthetic contracts only. No live model, browser, quality call, or upload."""
import copy
import unittest
from pathlib import Path
from llm_authoring import browser_form as form, official
from llm_authoring.core import Error, read_json, write_json, read_response
from llm_authoring.authoring import evaluation_template
import test_official_clients as clients


class BrowserFormTests(unittest.TestCase):
    setUp=clients.OfficialClientTests.setUp
    tearDown=clients.OfficialClientTests.tearDown
    candidate=clients.OfficialClientTests.candidate
    observed_question=clients.OfficialClientTests.observed_question
    seed_bundle=clients.OfficialClientTests.seed_bundle

    def evaluated(self,met=False):
        self.seed_bundle('合成Markdown：**原文**\n```json\n{"a":1}\n```')
        official.import_result(self.root,'seed')
        v=evaluation_template(self.root,('seed',));v['reviewer']='synthetic-author'
        for point in v['models']['seed']['points'].values():
            point.update(met=met,reason='合成逐点说明',quotes=['**原文**'] if met else [])
        return v

    def test_native_fields_keep_original_md_and_bound_images(self):
        v=self.evaluated();result=form.prepare(self.root,'seed',v)
        p=Path(result['spec']);job=form.validate_spec(p);item=read_response(self.root,'seed')
        self.assertEqual(job['text_fields']['doubao-markdown-input'],item['text'])
        self.assertIn('不满足',job['text_fields']['doubao-achievement-note-input'])
        self.assertEqual(job['selection']['label'],'未达成')
        self.assertEqual(job['binding']['item_id'],'200')
        self.assertEqual(len(job['screenshots']),1)
        self.assertTrue(Path(job['screenshots'][0]['file']).is_file())
        self.assertEqual(form.prepare(self.root,'seed',v)['spec'],str(p))

    def test_fully_attained_seed_cannot_enter_native_later_stage(self):
        with self.assertRaisesRegex(Error,'淘汰稿'):form.prepare(self.root,'seed',self.evaluated(True))
        self.assertFalse((self.root/'browser/model-fields').exists())

    def test_changed_reply_or_unverified_capture_cannot_prepare(self):
        v=self.evaluated();item=read_response(self.root,'seed')
        (item['directory']/'reply.md').write_text('changed')
        with self.assertRaises(Error):form.prepare(self.root,'seed',v)

    def test_changed_png_invalidates_prepared_contract(self):
        p=Path(form.prepare(self.root,'seed',self.evaluated())['spec']);job=read_json(p)
        Path(job['screenshots'][0]['file']).write_bytes(b'changed')
        with self.assertRaises(Error):form.validate_spec(p)

    def test_tampered_select_or_foreign_role_not_accepted(self):
        v=self.evaluated();p=Path(form.prepare(self.root,'seed',v)['spec']);job=read_json(p)
        job['selection']['label']='已达成';write_json(p,job)
        with self.assertRaisesRegex(Error,'哈希'):form.validate_spec(p)
        with self.assertRaises(Error):form.prepare(self.root,'arena_1',v)

    def test_new_rubric_invalidates_old_field_plan(self):
        v=self.evaluated();p=Path(form.prepare(self.root,'seed',v)['spec'])
        ev=copy.deepcopy(v);ev['rubric_sha256']='0'*64
        with self.assertRaises(Error):form.fields(self.root,'seed',ev)


if __name__=='__main__':unittest.main()
