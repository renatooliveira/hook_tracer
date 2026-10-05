"""Ensure the add-on scaffold can be imported outside Anki."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


class ScaffoldTests(unittest.TestCase):
    def test_import_does_not_load_anki_or_qt(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
import hook_tracer
import hook_tracer.core
assert not any(name.split('.')[0] in {'anki', 'aqt', 'PyQt6'} for name in sys.modules)
""",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_manifest(self):
        path = Path(__file__).resolve().parents[1] / "hook_tracer" / "manifest.json"
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest["package"], "hook_tracer")
        self.assertEqual(manifest["name"], "Hook Tracer")
