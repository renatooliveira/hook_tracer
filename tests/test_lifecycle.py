"""Exercise the Anki entry point with real Qt widgets and an isolated fake main window."""

import os
import subprocess
import sys


def test_lifecycle_offscreen():
    script = """
import anki.collection
import anki.hooks
import aqt
from aqt import gui_hooks
from aqt.qt import QApplication, QDialog, QMainWindow, QMenu, QPlainTextEdit
from types import SimpleNamespace

app = QApplication([])
class Manager:
    def getConfig(self, module):
        assert module == 'hook_tracer'
        return {'trace_on_startup': True}

mw = QMainWindow()
mw.app = app
mw.form = SimpleNamespace(menuTools=QMenu(mw))
mw.addonManager = Manager()
aqt.mw = mw
original = type(anki.hooks.note_will_flush).__call__
import hook_tracer
controller = hook_tracer.start(mw)
assert hook_tracer.start(mw) is controller
assert controller.patcher.recording
assert type(anki.hooks.note_will_flush).__call__ is not original
gui_hooks.main_window_did_init()
assert 'gui.main_window_did_init' in [e.hook for e in controller.recorder.snapshot()]
assert len(mw.form.menuTools.actions()) == 2
controller.open_action.trigger()
assert controller._dock is not None
first_dock = controller._dock
controller.open_action.trigger()
assert controller._dock is first_dock

console = QDialog()
console._log = QPlainTextEdit(console)
gui_hooks.debug_console_will_show(console)
anki.hooks.note_will_flush('test')
controller._flush(console, controller._timers[0])
assert 'anki.note_will_flush' in console._log.toPlainText()
controller.action.setChecked(False)
assert not controller.patcher.recording
before = len(controller.recorder.snapshot())
anki.hooks.note_will_flush('paused')
assert len(controller.recorder.snapshot()) == before
console.done(0)
hook_tracer.stop()
assert not first_dock.timer.isActive()
assert not controller._timers
assert len(mw.form.menuTools.actions()) == 0
assert type(anki.hooks.note_will_flush).__call__ is original
assert not gui_hooks.debug_console_will_show.count()
hook_tracer.stop()
mw.addonManager.getConfig = lambda module: None
paused = hook_tracer.start(mw)
assert not paused.patcher.recording
hook_tracer.stop()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
