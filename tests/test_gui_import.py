"""Probe Qt imports in a subprocess, keeping the headless test process clean."""

import os
import subprocess
import sys
import unittest


class GuiImportTests(unittest.TestCase):
    def test_discovery_needs_no_qapplication(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import anki.collection
import aqt.gui_hooks as hooks
from aqt.qt import QApplication
assert QApplication.instance() is None
found = []
for name, obj in vars(hooks).items():
    cls = type(obj)
    if cls.__name__.startswith('_') and cls.__name__.endswith(('Hook', 'Filter')):
        assert isinstance(vars(cls)['_hooks'], list)
        assert all(callable(getattr(obj, method)) for method in ('append', 'remove', 'count'))
        found.append(name)
assert 'card_will_show' in found
assert 'reviewer_did_answer_card' in found
assert QApplication.instance() is None
print(len(found))
""",
            ],
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertGreater(int(result.stdout.strip()), 0)
