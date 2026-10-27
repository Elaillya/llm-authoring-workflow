"""Synthetic pi-web adapter tests; never connect to a model service."""
from pathlib import Path
import shutil
import subprocess
import unittest


class PiWebTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js required')
    def test_node_contracts(self):
        scripts = [str(p) for p in Path(__file__).parent.glob('piweb_*.test.mjs')]
        result = subprocess.run([shutil.which('node'), '--test', *scripts], capture_output=True, text=True, encoding='utf-8', timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
