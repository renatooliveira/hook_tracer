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
    def __init__(self):
        self.config = {'trace_on_startup': True, 'buffer_size': 12}
    def getConfig(self, module):
        assert module == 'hook_tracer'
        return self.config
    def writeConfig(self, module, conf):
        assert module == 'hook_tracer'
        self.config = conf

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
assert controller.recorder._events.maxlen == 12
assert type(anki.hooks.note_will_flush).__call__ is not original
gui_hooks.main_window_did_init()
assert 'gui.main_window_did_init' in [e.hook for e in controller.recorder.snapshot()]
assert len(mw.form.menuTools.actions()) == 1
assert mw.form.menuTools.actions()[0].text() == 'Hook Tracer'
controller.open_action.trigger()
assert controller._dock is not None
first_dock = controller._dock
controller.open_action.trigger()
assert controller._dock is first_dock
assert first_dock.record_button.text() == 'Stop recording'
first_dock.catalog_button.click()
assert first_dock.pages.currentIndex() == 1
first_dock.stream_button.click()
assert first_dock.pages.currentIndex() == 0
controller.patcher.muted.add('gui.media_sync_did_progress')
assert mw.addonManager.config.get('muted_hooks') is None
first_dock.refresh()
assert 'not saved' in first_dock.mute_status.text()
first_dock.save_mutes.click()
assert 'match saved' in first_dock.mute_status.text()
assert mw.addonManager.config['muted_hooks'] == ['gui.media_sync_did_progress']
assert mw.addonManager.config['buffer_size'] == 12
controller.patcher.muted.clear()
assert mw.addonManager.config['muted_hooks'] == ['gui.media_sync_did_progress']

console = QDialog()
console._log = QPlainTextEdit(console)
gui_hooks.debug_console_will_show(console)
anki.hooks.note_will_flush('test')
controller._flush(console, controller._timers[0])
assert 'anki.note_will_flush' in console._log.toPlainText()
first_dock.record_button.click()
assert not controller.patcher.recording
assert first_dock.record_button.text() == 'Start recording'
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
mw.addonManager.config = {'trace_on_startup': False, 'trace_legacy': True,
                          'muted_hooks': ['anki.note_will_flush']}
paused = hook_tracer.start(mw)
assert not paused.patcher.recording
assert paused.patcher.muted == {'anki.note_will_flush'}
assert not paused.config.trace_legacy
assert 'unsupported' in paused.config_warnings[0]
paused.open_action.trigger()
assert paused._dock.record_button.text() == 'Start recording'
paused._dock.record_button.click()
assert paused.patcher.recording
assert paused._dock.record_button.text() == 'Stop recording'
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
