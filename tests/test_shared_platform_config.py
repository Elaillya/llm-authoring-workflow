"""Fresh-clone initialization uses only common metadata and no live service."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from threading import Barrier
from unittest.mock import patch
import json,tempfile,unittest
from llm_authoring import platform_client as client
from llm_authoring.core import Error,read_json
from llm_authoring.workspace import create_workspace
import test_platform_client as fixtures


class SharedConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.workspace=Path(self.temp.name)/'new-lab'
        create_workspace(self.workspace);self.task=self.workspace/'task'
    def tearDown(self):self.temp.cleanup()
    def test_public_metadata_has_no_login_session_or_original_item(self):
        value=client.default_config()
        self.assertEqual(value['referer'],'https://aidp.bytedance.com/')
        self.assertEqual(value['user_agent'],'Mozilla/5.0')
        self.assertIsNone(value['timeout_seconds'])
        self.assertEqual(set(value['checks']),{'question','criteria','attainment'})
        self.assertEqual(set(value),{'schema_version','endpoint','task_id','checks','referer',
            'timeout_seconds','user_agent','domain_labels','type_labels'})
        for item in value['checks'].values():self.assertEqual(set(item),{'plan_id','provider'})
        for secret in ('cookie','itemid','password','token','fs=','signature'):
            self.assertNotIn(secret,json.dumps(value).lower())
    def test_first_check_preparation_creates_local_configuration_without_network(self):
        with patch('llm_authoring.platform_client.call') as call:
            value,cookie=client.configuration(self.task);call.assert_not_called()
        self.assertEqual(value,client.default_config())
        self.assertEqual(read_json(self.workspace/'local/aidp/service.json'),value)
        self.assertTrue(cookie.is_file());self.assertEqual(cookie.stat().st_mode&0o777,0o600)
        with self.assertRaisesRegex(Error,'Cookie'):client.load_cookie(cookie)
    def test_existing_custom_configuration_and_cookie_are_never_replaced(self):
        result=client.setup(self.workspace,fixtures.config());cookie=Path(result['cookie_file'])
        cookie.write_text('sid=SYNTHETIC-PRIVATE-COOKIE')
        original=Path(result['service_file']).read_bytes();before=cookie.read_bytes()
        value,found=client.configuration(self.task)
        self.assertEqual(value['task_id'],'123');self.assertEqual(found.read_bytes(),before)
        self.assertEqual(Path(result['service_file']).read_bytes(),original)
    def test_same_project_default_setup_is_idempotent_with_existing_cookie(self):
        value,cookie=client.configuration(self.task);cookie.write_text('sid=SYNTHETIC-PRIVATE-COOKIE')
        before=cookie.read_bytes();client.setup(self.workspace,client.default_config())
        self.assertEqual(cookie.read_bytes(),before)
    def test_cli_default_setup_does_not_ask_for_har(self):
        from llm_authoring.cli import main
        out=StringIO()
        with patch('llm_authoring.platform_client.call') as call,redirect_stdout(out),redirect_stderr(StringIO()):
            result=main(['--workspace',str(self.workspace),'--task',str(self.task),'qa-setup','--default'])
            call.assert_not_called()
        self.assertEqual(result,0);self.assertIn('cookie.txt',out.getvalue())
        self.assertTrue((self.workspace/'local/aidp/service.json').is_file())
    def test_two_windows_initialize_the_same_complete_configuration(self):
        barrier=Barrier(2)
        def prepare():barrier.wait(timeout=3);return client.configuration(self.task)[0]
        with ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(lambda _:prepare(),range(2)))
        self.assertEqual(values,[client.default_config()]*2)
        self.assertEqual(read_json(self.workspace/'local/aidp/service.json'),values[0])
    def test_racing_custom_configuration_is_preserved(self):
        custom=fixtures.config();target=self.workspace/'local/aidp/service.json'
        def competitor(source,destination):
            target.write_text(json.dumps(custom));raise FileExistsError('synthetic competing setup')
        with patch('llm_authoring.platform_client.os.link',side_effect=competitor):
            with self.assertRaises(Error):client.setup(self.workspace,client.default_config())
        self.assertEqual(read_json(target),custom)
