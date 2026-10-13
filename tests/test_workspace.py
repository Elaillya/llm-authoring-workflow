import json
from pathlib import Path
import tempfile
import unittest
from llm_authoring.workspace import TOOL_ROOT,begin,choose_domain,choose_type,create_task,create_workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'我的 工作区'
        create_workspace(self.root);self.task=self.root/'task'
    def tearDown(self):self.tmp.cleanup()
    def fill_config(self,select_domain=True):
        file=self.root/'local/providers.json';value=json.loads((TOOL_ROOT/'config/providers.example.json').read_text())
        for p in value['providers'].values():p['base_url']='https://example.com/v1/';p['api_key']='synthetic-private-fixture'
        file.write_text(json.dumps(value));file.chmod(0o600)
        if select_domain:choose_domain(self.task,'计算机科学')
    def test_first_use_requests_domain_and_type_without_configuration(self):
        result=begin(self.task,self.root)
        self.assertEqual(result['requires_input'],['domain','question_type'])
        self.assertEqual(len(result['question_type_choices']),3)
        self.assertEqual(len(result['models']),3)
        self.assertFalse((self.root/'local/providers.json').exists())
    def test_configured_user_only_needs_type_then_assistant_supplies_scenario(self):
        self.fill_config(select_domain=False);result=begin(self.task,self.root)
        self.assertEqual(result['requires_input'],['domain','question_type'])
        choose_domain(self.task,'材料科学')
        choose_type(self.task,'How-to类');result=begin(self.task,self.root)
        self.assertTrue(result['ready']);self.assertEqual(result['scenario_owner'],'assistant')
    def test_new_task_asks_type_without_requiring_credentials_again(self):
        self.fill_config();choose_type(self.task,'How-to类')
        new=create_task(self.root,'question-002')
        self.assertEqual(begin(Path(new['task']),self.root)['requires_input'],['domain','question_type'])
        self.assertTrue((Path(new['task'])/'.git').is_dir())
        self.assertNotIn('arena-inbox',[p.name for p in Path(new['task']).iterdir()])
    def test_renamed_task_retains_frozen_evidence_and_is_default_with_separate_new_task(self):
        from llm_authoring.workspace import rename_task,update_workspace
        from llm_authoring.core import freeze,sha,write_json
        from test_core import question,populate
        self.fill_config();choose_type(self.task,'分析决策类')
        q=question();q['task_id']='question-001';freeze(self.task,q)
        write_json(self.task/'evaluations/three-r0001.json',populate(self.task))
        protected=[p for p in self.task.rglob('*') if p.is_file() and any(n in p.parts for n in ['revisions','responses','evaluations','drafts'])]
        before={str(p.relative_to(self.task)):sha(p) for p in protected}
        config=(self.root/'local/providers.json').read_bytes()
        result=rename_task(self.root,self.task,'cs_47')
        renamed=Path(result['task'])
        self.assertEqual(renamed,self.root/'tasks/cs_47')
        self.assertTrue(self.task.is_symlink())
        self.assertEqual(self.task.resolve(),renamed)
        task=json.loads((renamed/'TASK.json').read_text())
        self.assertEqual(task['task_id'],'question-001')
        self.assertEqual(task['display_id'],'cs_47')
        self.assertEqual(before,{p:sha(renamed/p) for p in before})
        self.assertEqual(json.loads((self.root/'.authoring-workspace.json').read_text())['default_task'],'tasks/cs_47')
        self.assertTrue((renamed/'cs_47.code-workspace').is_file())
        new=create_task(self.root,'cs_35')
        self.assertEqual(begin(Path(new['task']),self.root)['requires_input'],['domain','question_type'])
        self.assertFalse((Path(new['task'])/'CURRENT.json').exists())
        self.assertEqual(config,(self.root/'local/providers.json').read_bytes())
        from llm_authoring.cli import main
        from contextlib import redirect_stdout
        from io import StringIO
        output=StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['--workspace',str(self.root),'status']),0)
        self.assertEqual(json.loads(output.getvalue())['revision'],'r0001')
        update=update_workspace(self.root)
        self.assertEqual(len(update['tasks']),2)
        self.assertEqual(before,{p:sha(renamed/p) for p in before})
    def test_rename_conflict_does_not_move_current_task(self):
        from llm_authoring.workspace import rename_task
        from llm_authoring.core import Error
        create_task(self.root,'cs_35')
        with self.assertRaises(Error):rename_task(self.root,self.task,'cs_35')
        with self.assertRaises(Error):rename_task(self.root,self.task,'../outside')
        self.assertTrue((self.task/'TASK.json').is_file())
    def test_rename_preserves_custom_window_settings_and_rejects_window_collision(self):
        from llm_authoring.workspace import rename_task
        from llm_authoring.core import Error,read_json,write_json
        old=self.task/'question-001.code-workspace'
        config=read_json(old);config['settings']={'editor.fontSize':17}
        write_json(old,config)
        collision=self.task/'cs_47.code-workspace'
        collision.write_text('existing user workspace')
        with self.assertRaises(Error):rename_task(self.root,self.task,'cs_47')
        self.assertEqual(collision.read_text(),'existing user workspace')
        self.assertFalse((self.root/'tasks/cs_47').exists())
        collision.unlink()
        result=rename_task(self.root,self.task,'cs_47')
        self.assertEqual(read_json(result['workspace_file'])['settings'],config['settings'])
    def test_failed_rename_restores_previous_directory_and_metadata(self):
        from llm_authoring.workspace import rename_task
        from unittest.mock import patch
        paths=[self.task/'TASK.json',self.task/'AGENTS.md',self.task/'question-001.code-workspace',self.root/'.authoring-workspace.json',self.root/'Authoring.code-workspace']
        before={p:p.read_bytes() for p in paths}
        with patch('llm_authoring.workspace.write_json',side_effect=OSError('synthetic write failure')):
            with self.assertRaises(OSError):rename_task(self.root,self.task,'cs_47')
        self.assertTrue(self.task.is_dir());self.assertFalse(self.task.is_symlink())
        self.assertFalse((self.root/'tasks/cs_47').exists())
        self.assertEqual(before,{p:p.read_bytes() for p in paths})
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
    def test_legacy_collection_commands_are_disabled_without_any_network(self):
        from contextlib import redirect_stderr,redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        from llm_authoring.cli import main
        args=['--workspace',str(self.root),'--task',str(self.task)]
        for command in [('collect','seed','--allow-live'),('collect','gpt','--allow-live'),('collect','claude','--allow-live'),('recover','seed','fixture.json'),('render','seed')]:
            with patch('llm_authoring.cli.collect') as collect,patch('llm_authoring.cli.recover') as recover,patch('llm_authoring.cli.render_response') as render,redirect_stderr(StringIO()),redirect_stdout(StringIO()):
                self.assertEqual(main(args+list(command)),2)
                collect.assert_not_called();recover.assert_not_called();render.assert_not_called()
