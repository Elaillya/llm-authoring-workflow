"""Synthetic fixtures only; no real model or professional acceptance evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from llm_authoring.core import Error,freeze,save_response,write_json,sha


def question():
    return {'schema_version':1,'task_id':'test-only','domain':'计算机科学','prompt':'上线前，先核对验收依据还是先批量生成代码？','question_type':'分析决策类',
            'insight':{'mechanism':'测试机制','priority':'测试优先级','conclusion':'测试结论'},'author_notes':'合成测试，不代表用户经历或有效题目。',
            'points':[{'id':'D1','kind':'decisive','criterion':'明确先核对验收依据。'},{'id':'D2','kind':'decisive','criterion':'解释依据如何约束实现。'}]}


def prepared(root):
    notes=Path(root)/'drafts/sources.md';notes.parent.mkdir(parents=True,exist_ok=True)
    notes.write_text('# 合成来源夹具\n\n没有真实专业来源，仅测试格式和版本约束。\n')
    write_json(Path(root)/'REQUEST.json',{'question_type':'分析决策类','domain':'计算机科学','domain_confirmed':True})
    freeze(root,question())


def populate(root):
    from llm_authoring.authoring import evaluation_template
    for role,name in [('seed','Seed 2.1 Turbo'),('gpt','GPT-5.6 sol'),('claude','Claude Opus 4.6')]:
        text='# 合成回复\n\n先核对验收依据；依据约束实现。\n'
        options={'reasoning':{'effort':'high'}} if role=='gpt' else {'thinking':{'type':'adaptive'},'output_config':{'effort':'high'}} if role=='claude' else {}
        save_response(root,role,text,{'display_name':name,'model':name,'returned_model':name,'source_kind':'api','completion_status':'complete','request_options':options},raw=b'{"fixture":"TEST ONLY"}')
    ev=evaluation_template(root);ev['reviewer']='test-fixture'
    for role in ev['models']:
        for point in ev['models'][role]['points']:
            ev['models'][role]['points'][point]={'met':role!='seed','reason':'合成工具测试，不是内容正确性判断。','quotes':['先核对验收依据'] if role!='seed' else []}
    return ev


class AuthoringTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);prepared(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_type_must_be_selected_first(self):
        root=self.root/'new-task'
        with self.assertRaises(Error):freeze(root,question())
    def test_different_type_cannot_be_frozen(self):
        q=question();q['question_type']='How-to类'
        with self.assertRaisesRegex(Error,'题型'):freeze(self.root,q)
    def test_gate_uses_all_decisive_points_of_three_models(self):
        from llm_authoring.authoring import check_three
        ev=populate(self.root);ev['models']['claude']['points']['D2']={'met':False,'reason':'测试缺失','quotes':[]}
        result=check_three(self.root,ev)
        self.assertTrue(result['three_model_gate']);self.assertFalse(result['models']['claude']['attained'])
        self.assertNotIn('ranking',result)
    def test_missing_response_is_not_failure(self):
        from llm_authoring.authoring import evaluation_template
        with self.assertRaisesRegex(Error,'完整回复'):evaluation_template(self.root)
    def test_supporting_points_do_not_become_authoring_pass_gate(self):
        from llm_authoring.authoring import evaluation_template
        q=question();q['points'].append({'id':'N1','kind':'supporting','criterion':'可选辅助标准。'});freeze(self.root,q)
        ev=populate(self.root)
        self.assertEqual(set(ev['models']['seed']['points']),{'D1','D2'})
    def test_rubric_change_requires_uniform_re_evaluation(self):
        from llm_authoring.authoring import check_three
        ev=populate(self.root);q=question();q['points'][0]['criterion']='修订标准';freeze(self.root,q)
        with self.assertRaisesRegex(Error,'考点版本'):check_three(self.root,ev)
    def test_quotes_must_match_original(self):
        from llm_authoring.authoring import check_three
        ev=populate(self.root);ev['models']['gpt']['points']['D1']['quotes']=['不存在的句子']
        with self.assertRaisesRegex(Error,'引用'):check_three(self.root,ev)
    def test_insight_change_requires_current_version_judgments(self):
        from llm_authoring.authoring import check_three
        ev=populate(self.root);q=question();q['insight']['conclusion']='修订结论';freeze(self.root,q)
        with self.assertRaisesRegex(Error,'完整冻结版本'):check_three(self.root,ev)
    def test_whitespace_is_included_in_100_character_limit(self):
        q=question();q['prompt']='字'*100+'\n'
        with self.assertRaisesRegex(Error,'100'):freeze(self.root,q)
    def test_seed_screen_can_run_before_other_replies(self):
        from llm_authoring.authoring import evaluation_template,check_seed
        save_response(self.root,'seed','# 答复\n\n没有给出所需判断。',{'display_name':'Seed 2.1 Turbo','source_kind':'api','completion_status':'complete'},raw=b'{"fixture":"TEST"}')
        ev=evaluation_template(self.root,('seed',));ev['reviewer']='synthetic-fixture'
        for j in ev['models']['seed']['points'].values():j.update({'met':False,'reason':'合成测试缺失','quotes':[]})
        self.assertTrue(check_seed(self.root,ev)['continue_to_gpt_claude'])
