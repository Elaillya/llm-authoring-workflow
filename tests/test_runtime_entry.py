"""Native launcher and setup reuse with synthetic directories; no dependency downloads."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from llm_authoring.workspace import create_workspace,update_workspace
from llm_authoring.core import read_json,write_json


class RuntimeEntryTests(unittest.TestCase):
    def test_unicode_space_path_uses_existing_interpreter_and_utf8(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'中文 工作区'
            create_workspace(root,runtime={'python':sys.executable})
            runtime=read_json(root/'local/runtime.json')
            window=read_json(root/'Authoring.code-workspace')
            self.assertEqual(window['tasks']['tasks'][0]['command'],sys.executable)
            command=[sys.executable,'-X','utf8',str(root/'bin/lab'),'status']
            env={**os.environ,'PYTHONUTF8':'0','PYTHONIOENCODING':'ascii'}
            result=subprocess.run(command,capture_output=True,encoding='utf-8',env=env)
            self.assertEqual(result.returncode,0,result.stderr)
            json.loads(result.stdout)
            update_workspace(root)
            self.assertEqual(read_json(root/'local/runtime.json'),runtime)

    def test_setup_reuses_verified_environment_without_install(self):
        script=Path(__file__).parents[1]/'scripts/setup.py'
        spec=importlib.util.spec_from_file_location('workflow_setup',script)
        setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);python=root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            python.parent.mkdir(parents=True);python.write_bytes(b'synthetic interpreter')
            (root/'requirements.lock').write_text('Pillow==12.3.0',encoding='utf-8')
            with patch.object(setup.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run,patch.object(setup.venv,'EnvBuilder') as builder:
                self.assertEqual(setup.prepare(root),python)
                builder.assert_not_called();self.assertEqual(run.call_count,1)
                self.assertEqual(run.call_args.kwargs['env']['PYTHONUTF8'],'1')
