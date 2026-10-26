"""Regression checks against invalid public-package fixtures."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackageValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='foundercraft-validation-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        shutil.copytree(ROOT, self.repo,
                        ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__', '.cache'))
        subprocess.run(['git', 'init', '--quiet'], cwd=self.repo, check=True)

    def write_json(self, name, transform):
        path = self.repo / name
        data = json.loads(path.read_text())
        transform(data)
        path.write_text(json.dumps(data, ensure_ascii=False))

    def check_failure(self, message):
        result = subprocess.run([sys.executable, 'scripts/check.py'], cwd=self.repo,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)

    def test_rejects_education_even_when_overlay_and_catalog_match(self):
        def portable(data):
            data['extensions']['com.openai']['interface']['category'] = 'Education'

        def legacy(data):
            data['interface']['category'] = 'Education'

        def marketplace(data):
            data['plugins'][0]['category'] = 'Education'

        self.write_json('plugins/foundercraft/plugin.json', portable)
        self.write_json('plugins/foundercraft/.codex-plugin/plugin.json', legacy)
        self.write_json('.agents/plugins/marketplace.json', marketplace)
        self.check_failure('Unsupported OpenAI interface.category')

    def test_rejects_nonstring_marketplace_category(self):
        def marketplace(data):
            data['plugins'][0]['category'] = 42

        self.write_json('.agents/plugins/marketplace.json', marketplace)
        self.check_failure('Marketplace category must be a nonblank string')


if __name__ == '__main__':
    unittest.main()
