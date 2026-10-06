"""Export confirmation, cancellation and failure on the offscreen dock."""

import os
import subprocess
import sys


def test_export_ui_offscreen(tmp_path):
    script = """
import json
from pathlib import Path
from unittest.mock import patch
from aqt.qt import QApplication, QMainWindow, QMessageBox
from hook_tracer.core.recorder import Recorder
from hook_tracer.core.patching import Patcher
from hook_tracer.ui import dock as module

app = QApplication([])
mw = QMainWindow()
r = Recorder()
p = Patcher(r)
r.record(hook='gui.hidden', kind='hook', started_ns=1, ended_ns=2,
         callbacks=(), args=('private card',), filter_in=None, result=None,
         input_value=None, error=None)
def fail_save(_):
    raise OSError('write denied')
dock = module.StreamDock(mw, p, r, lambda _: None, persist_mutes=fail_save)
dock.search.setText('not present')
assert dock.model.rowCount() == 0
out = Path(__import__('sys').argv[1]) / 'trace.jsonl'
buttons = QMessageBox.StandardButton
with patch.object(module, 'QMessageBox') as box, patch.object(module, 'QFileDialog') as file:
    box.StandardButton = buttons
    dock.save_mutes.click()
    box.warning.assert_called_once()
    box.warning.reset_mock()
    box.question.return_value = buttons.No
    dock.export.click()
    file.getSaveFileName.assert_not_called()
    box.question.return_value = buttons.Yes
    file.getSaveFileName.return_value = ('', '')
    dock.export.click()
    assert not out.exists()
    file.getSaveFileName.return_value = (str(out), '')
    dock.export.click()
    row = json.loads(out.read_text().strip())
    assert row['hook'] == 'gui.hidden' and row['args'] == ['private card']
    file.getSaveFileName.return_value = (str(out.parent), '')
    dock.export.click()
    box.warning.assert_called_once()
    assert list(out.parent.glob('*.tmp')) == []
dock.shutdown()
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
