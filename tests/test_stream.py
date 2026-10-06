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
from hook_tracer.ui.catalog import CatalogModel, catalog_table
from hook_tracer.ui.detail import describe, render_event
from hook_tracer.core.discovery import discover
from tests import fake_hooks as fake

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
mw.resize(1200, 900)
dock = StreamDock(mw, p, r, lambda value: setattr(p, 'recording', value))
mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
mw.show()
dock.show()
app.processEvents()
assert dock.model.rowCount() == 1
assert dock.splitter.sizes()[0] > dock.splitter.sizes()[1]
dock.splitter.setSizes([200, 500])
assert dock.splitter.sizes()[1] > dock.splitter.sizes()[0]
r.note_error()
dock.refresh()
assert 'Recording errors: 1' in dock.errors.text()
dock.hide()
assert not dock.timer.isActive()
dock.show()
app.processEvents()
assert dock.model.rowCount() == 1
dock.table.setCurrentIndex(dock.model.index(0, 1))
assert 'gui.after_clear' in dock.detail.toPlainText()
assert 'Arguments' in dock.detail.toPlainText()
dock.detail.copy_button.click()
assert app.clipboard().text() == describe(dock.model.event_at(0))
dock.mute.click()
assert 'gui.after_clear' in p.muted
assert dock.muted.count() == 1
dock.unmute.click()
assert not p.muted
dock.record_button.click()
assert not p.recording
assert dock.record_button.text() == 'Start recording'
dock.regex.setChecked(True)
dock.search.setText('[')
assert dock.filter_message.text().startswith('Invalid regex')
dock.search.clear()
last_event = r.snapshot()[0]
dock.clear.click()
assert dock.model.rowCount() == 0
assert 'Select a trace event.' in dock.detail.toPlainText()
assert not dock.detail.copy_button.isEnabled()
dock.hide()
assert not dock.timer.isActive()
dock.shutdown()
assert describe(None) == 'Select a trace event.'
assert '<argument capture disabled>' in describe(last_event, False)
from dataclasses import replace
filtered = replace(last_event, kind='filter', filter_in="'x'", filter_out="'y'", changed=True)
assert "Filter input: 'x'" in describe(filtered)
assert "Filter output: 'y'" in describe(filtered)
assert 'Changed: True' in describe(filtered)
failed = replace(filtered, filter_out=None, changed=None, error='ValueError: failed')
assert 'Filter output: <dispatch failed>' in describe(failed)
assert 'Error: ValueError: failed' in describe(failed)
assert 'Filter' in render_event(filtered)
assert 'Error' in render_event(failed)
injected = replace(last_event, args=("<script>alert('x')</script>",))
assert '<script>' not in render_event(injected)
assert '&lt;script&gt;' in render_event(injected)
fake._DidSomethingHook._hooks = []
infos = discover([('anki', fake)])
p.install(infos)
p.recording = True
catalog, catalog_model = catalog_table(infos, p, r)
def cb(value):
    return None
cb.__module__ = 'demo_addon.handlers'
r.add_on_names['demo_addon'] = 'Demo'
fake.did_something.append(cb)
catalog_model.refresh()
row = next(row for row in catalog_model.rows if row[0] == 'anki.did_something')
assert row[3] == 1 and 'Demo' in row[4]
fake.did_something('payload')
catalog_model.refresh()
row = next(row for row in catalog_model.rows if row[0] == 'anki.did_something')
assert row[2] == 1
assert 'Demo' in describe(r.snapshot()[-1])
fake.did_something.remove(cb)
catalog_model.refresh()
row = next(row for row in catalog_model.rows if row[0] == 'anki.did_something')
assert row[3] == 0 and row[2] == 1
catalog.sortByColumn(3, Qt.SortOrder.DescendingOrder)
assert catalog.model().data(catalog.model().index(0, 3), Qt.ItemDataRole.UserRole) >= 0
p.uninstall()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
