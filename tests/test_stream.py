"""Offscreen Qt model and dock tests; no real profile required."""

import os
import subprocess
import sys


def test_stream_offscreen():
    script = """
from aqt.qt import QApplication, QMainWindow, Qt
from hook_tracer.core.recorder import Recorder
from hook_tracer.core.patching import Patcher
from hook_tracer.ui.stream_model import StreamModel
from hook_tracer.ui.dock import StreamDock

app = QApplication([])
r = Recorder(buffer_size=3)
p = Patcher(r)
p.recording = True
model = StreamModel(r)
def fire(name, callbacks=()):
    r.record(hook=name, kind='hook', started_ns=100, ended_ns=200,
             callbacks=callbacks, args=('arg',), filter_in=None,
             result=None, input_value=None, error=None)

fire('gui.first')
model.refresh()
assert model.rowCount() == 1
assert model.data(model.index(0, 1)) == 'gui.first'
assert model.headerData(1, Qt.Orientation.Horizontal) == 'Hook'
fire('gui.second', (('callback', 'owner'),))
fire('anki.third')
model.refresh()
assert model.rowCount() == 3
fire('gui.fourth')
model.refresh()
assert model.rowCount() == 3
assert model.event_at(0).hook == 'gui.second'
model.set_filters('^gui[.]', True, True)
assert model.rowCount() == 1
assert model.event_at(0).hook == 'gui.second'
model.set_filters('[', True, False)
assert model.filter_error and model.rowCount() == 0
fire('gui.during_invalid_regex')
model.refresh()
assert model.rowCount() == 0 and r.snapshot()[-1].hook == 'gui.during_invalid_regex'
model.set_filters('gui', False, False)
assert model.rowCount() == 2
r.clear()
model.refresh()
assert model.rowCount() == 0
fire('gui.after_clear')
model.refresh()
assert model.rowCount() == 1
assert model.event_at(0).seq == 6
for i in range(100):
    fire(f'gui.bulk_{i}')
model.refresh()
assert model.rowCount() == 3
assert model.event_at(0).hook == 'gui.bulk_97'
from threading import Thread
worker = Thread(target=lambda: fire('gui.background'), name='worker')
worker.start()
worker.join()
model.refresh()
assert model.data(model.index(2, 1), Qt.ItemDataRole.BackgroundRole) is not None
r.clear()
model.refresh()
fire('gui.after_clear')

mw = QMainWindow()
dock = StreamDock(mw, p, r, lambda value: setattr(p, 'recording', value))
mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
mw.show()
dock.show()
app.processEvents()
assert dock.model.rowCount() == 1
dock.hide()
assert not dock.timer.isActive()
dock.show()
app.processEvents()
assert dock.model.rowCount() == 1
dock.table.setCurrentIndex(dock.model.index(0, 1))
dock.mute.click()
assert 'gui.after_clear' in p.muted
assert dock.muted.count() == 1
dock.unmute.click()
assert not p.muted
dock.pause.click()
assert not p.recording
dock.regex.setChecked(True)
dock.search.setText('[')
assert dock.filter_message.text().startswith('Invalid regex')
dock.search.clear()
dock.clear.click()
assert dock.model.rowCount() == 0
dock.hide()
assert not dock.timer.isActive()
dock.shutdown()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
