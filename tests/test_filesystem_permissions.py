"""Workspace objects inherit OS permissions and retain exclusive/atomic semantics."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from llm_authoring.filesystem import temporary_directory,temporary_file
from llm_authoring.core import freeze_record,write_json
from llm_authoring.platform_client import setup
from llm_authoring.workspace import create_workspace
from test_core import question
from test_platform_client import config


class FilesystemPermissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()

    def test_exclusive_staging_collision_preserves_existing_contents(self):
        (self.root/'stage-fixed').mkdir();(self.root/'file-fixed').write_text('original')
        with patch('llm_authoring.filesystem.uuid.uuid4') as identity:
            identity.return_value.hex='fixed'
            with self.assertRaises(FileExistsError):temporary_directory(self.root,'stage-')
            with self.assertRaises(FileExistsError):temporary_file(self.root,'file-')
        self.assertEqual((self.root/'file-fixed').read_text(),'original')

    def test_atomic_json_failure_keeps_old_file(self):
        target=self.root/'test.json';write_json(target,{'old':True})
        with patch('llm_authoring.core.os.replace',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):write_json(target,{'new':True})
        self.assertEqual(json.loads(target.read_text()),{'old':True})
        self.assertEqual([p.name for p in self.root.iterdir()],['test.json'])

    @unittest.skipUnless(os.name=='nt' and (shutil.which('powershell') or shutil.which('pwsh')),'Windows ACL check')
    def test_published_freeze_and_workspace_directories_inherit_windows_acl(self):
        ws=self.root/'workspace';created=create_workspace(ws,first_task='test')
        task=Path(created['first_task']['task']);q=question();q['task_id']='test';freeze_record(task,q)
        platform=setup(ws,config())
        published=temporary_directory(task,'export-');(published/'提交信息.md').write_text('合成材料',encoding='utf-8')
        paths=[ws,ws/'local',task/'revisions/r0001',published,Path(platform['cookie_file']).parent]
        # JSON argument avoids shell interpolation of the test paths.
        environment={**os.environ,'AUTHORING_ACL_TEST_PATHS':json.dumps(list(map(str,paths)))}
        command='$paths=ConvertFrom-Json $env:AUTHORING_ACL_TEST_PATHS; @($paths | ForEach-Object { (Get-Acl -LiteralPath $_).AreAccessRulesProtected }) | ConvertTo-Json -Compress'
        run=subprocess.run([shutil.which('powershell') or shutil.which('pwsh'),'-NoProfile','-NonInteractive','-Command',command],env=environment,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout),[False]*len(paths))

    @unittest.skipUnless(os.name=='nt' and (shutil.which('powershell') or shutil.which('pwsh')),'Windows ACL recovery')
    def test_legacy_acl_repair_preserves_bytes_and_is_idempotent(self):
        ws=self.root/'old-workspace';create_workspace(ws,first_task='test')
        old=ws/'question-test/legacy';old.mkdir(mode=0o700)
        original=old/'original.md';original.write_bytes(b'unchanged evidence')
        script=Path(__file__).resolve().parents[1]/'scripts/repair_workspace_permissions.ps1'
        shell=shutil.which('powershell') or shutil.which('pwsh')
        def run(name,apply=False):
            args=[shell,'-NoProfile','-NonInteractive','-File',str(script),'-WorkspaceRoots',str(ws),'-BackupFile',str(self.root/name)]
            if apply:args+=['-Apply']
            result=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads(result.stdout)
        first=run('before.json',True)
        self.assertEqual(first['Changed'],first['Matched'])
        if first['Matched']==0:self.skipTest('This Python runtime does not create restricted Windows directories for mode 700')
        self.assertEqual(first['Matched'],1)
        self.assertEqual(original.read_bytes(),b'unchanged evidence')
        self.assertEqual(run('after.json')['Matched'],0)
