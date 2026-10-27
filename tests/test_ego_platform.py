"""Exercise the shipped browser helper against a synthetic DOM, without a browser."""
from pathlib import Path
import shutil
import subprocess
import unittest


class EgoPlatformTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for browser-helper unit tests')
    def test_browser_helper_contracts(self):
        scripts = [Path(__file__).with_name(name) for name in ('ego_platform.test.mjs', 'platform_stages.test.mjs','observation_window.test.mjs')]
        result = subprocess.run(
            [shutil.which('node'), '--test', *map(str, scripts)],
            capture_output=True, text=True, encoding='utf-8', timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
