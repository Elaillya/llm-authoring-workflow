import json
from pathlib import Path
import tempfile
import unittest
from llm_authoring.workspace import TOOL_ROOT,begin,choose_type,create_task,create_workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'我的 工作区'
        create_workspace(self.root);self.task=self.root/'task'
    def tearDown(self):self.tmp.cleanup()
    def fill_config(self):
        file=self.root/'local/providers.json';value=json.loads(file.read_text())
        for p in value['providers'].values():p['base_url']='https://example.com/v1/';p['api_key']='synthetic-private-fixture'
        file.write_text(json.dumps(value));file.chmod(0o600)
    def test_first_use_requests_type_and_three_model_configuration(self):
        result=begin(self.task,self.root)
        self.assertEqual(result['requires_input'],['question_type','model_configuration'])
        self.assertEqual(len(result['question_type_choices']),3)
        self.assertEqual(len(result['models']),3)
        self.assertEqual((self.root/'local/providers.json').stat().st_mode&0o777,0o600)
    def test_configured_user_only_needs_type_then_assistant_supplies_scenario(self):
        self.fill_config();result=begin(self.task,self.root)
        self.assertEqual(result['requires_input'],['question_type'])
        choose_type(self.task,'How-to类');result=begin(self.task,self.root)
        self.assertTrue(result['ready']);self.assertEqual(result['scenario_owner'],'assistant')
    def test_new_task_asks_type_without_requiring_credentials_again(self):
        self.fill_config();choose_type(self.task,'How-to类')
        new=create_task(self.root,'question-002')
        self.assertEqual(begin(Path(new['task']),self.root)['requires_input'],['question_type'])
        self.assertTrue((Path(new['task'])/'.git').is_dir())
        self.assertNotIn('arena-inbox',[p.name for p in Path(new['task']).iterdir()])
    def test_workspace_and_private_config_are_not_overwritten(self):
        from llm_authoring.core import Error
        self.fill_config();before=(self.root/'local/providers.json').read_bytes()
        with self.assertRaises(Error):create_workspace(self.root)
        self.assertEqual((self.root/'local/providers.json').read_bytes(),before)
    def test_arena_import_is_available_but_does_not_invent_missing_evidence(self):
        from llm_authoring.cli import main
        from contextlib import redirect_stderr,redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        with patch('llm_authoring.cli.collect') as network,redirect_stderr(StringIO()),redirect_stdout(StringIO()):
            self.assertEqual(main(['--workspace',str(self.root),'--task',str(self.task),'arena-import']),2)
            network.assert_not_called()
    def test_update_keeps_current_question_originals_config_and_old_delivery(self):
        from llm_authoring.workspace import update_workspace
        from llm_authoring.core import freeze,write_json,sha
        from test_core import question,populate
        self.fill_config();choose_type(self.task,'分析决策类')
        q=question();q['task_id']='question-001';freeze(self.task,q)
        notes=self.task/'drafts/sources.md';notes.write_text('合成来源，测试升级不修改现有材料。')
        ev=populate(self.task);write_json(self.task/'evaluations/three-r0001.json',ev)
        old=self.task/'delivery/v001/handoff.json';write_json(old,{'workflow_version':'1.0.1','next_workflow':'quality_review_and_ranking'})
        log=self.task/'WORKLOG.md';log.write_text('历史工作记录：上半部分已完成，原始判断保留。\n')
        protected=[p for p in self.task.rglob('*') if p.is_file() and any(name in p.parts for name in ['revisions','responses','delivery','evaluations','drafts'])]
        protected += [self.task/'REQUEST.json',self.task/'CURRENT.json',self.task/'TASK.json',self.root/'local/providers.json',self.root/'local/runtime.json']
        before={str(p):sha(p) for p in protected}
        result=update_workspace(self.root)
        self.assertTrue(result['tasks'][0]['preserved_existing_question'])
        self.assertEqual(before,{str(p):sha(p) for p in protected})
        self.assertTrue(log.read_text().endswith('历史工作记录：上半部分已完成，原始判断保留。\n'))
        self.assertTrue(Path(result['instructions_backup']).is_dir())
        slot=Path(result['tasks'][0]['arena']['input_files']['arena_1']);slot.write_text('用户已填内容，不允许覆盖')
        update_workspace(self.root)
        self.assertEqual(slot.read_text(),'用户已填内容，不允许覆盖')
        self.assertEqual(before,{str(p):sha(p) for p in protected})
    def test_gpt_call_is_blocked_until_seed_current_version_fails(self):
        from contextlib import redirect_stderr,redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        from llm_authoring.cli import main
        from llm_authoring.authoring import evaluation_template
        from llm_authoring.core import freeze,save_response,write_json
        from test_core import question
        self.fill_config();choose_type(self.task,'分析决策类');q=question();q['task_id']='question-001';freeze(self.task,q)
        save_response(self.task,'seed','先核对验收依据。',{'display_name':'Seed 2.1 Turbo','source_kind':'api','completion_status':'complete'},raw=b'{"fixture":"TEST ONLY"}')
        args=['--workspace',str(self.root),'--task',str(self.task),'collect','gpt','--allow-live']
        with patch('llm_authoring.cli.collect') as network,redirect_stderr(StringIO()),redirect_stdout(StringIO()):
            self.assertEqual(main(args),2);network.assert_not_called()
        ev=evaluation_template(self.task,('seed',));ev['reviewer']='synthetic-fixture'
        for j in ev['models']['seed']['points'].values():j.update({'met':True,'reason':'测试满足','quotes':['先核对验收依据']})
        probe=self.task/'evaluations/seed-r0001.json';write_json(probe,ev)
        with patch('llm_authoring.cli.collect') as network,redirect_stderr(StringIO()),redirect_stdout(StringIO()):
            self.assertEqual(main(args),2);network.assert_not_called()
        for j in ev['models']['seed']['points'].values():j.update({'met':False,'reason':'测试未满足','quotes':[]})
        ev['models']['seed']['points']['D1']['met']=None;write_json(probe,ev)
        with patch('llm_authoring.cli.collect') as network,redirect_stderr(StringIO()),redirect_stdout(StringIO()):
            self.assertEqual(main(args),2);network.assert_not_called()
        ev['models']['seed']['points']['D1']['met']=False
        current_hash=ev['question_sha256'];ev['question_sha256']='stale';write_json(probe,ev)
        with patch('llm_authoring.cli.collect') as network,redirect_stderr(StringIO()),redirect_stdout(StringIO()):
            self.assertEqual(main(args),2);network.assert_not_called()
        ev['question_sha256']=current_hash
        write_json(probe,ev)
        with patch('llm_authoring.cli.collect',return_value={'fixture':'test only'}) as network,redirect_stdout(StringIO()):
            self.assertEqual(main(args),0);network.assert_called_once()
