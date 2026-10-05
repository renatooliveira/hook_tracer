"""Run with `uv run python -m examples.trace_note` (disposable collection)."""

import tempfile
from pathlib import Path

import anki.collection  # noqa: F401 - import before hooks
import anki.hooks
from anki.collection import Collection

from hook_tracer.core.discovery import discover
from hook_tracer.core.patching import Patcher
from hook_tracer.core.recorder import Recorder

with tempfile.TemporaryDirectory() as temp:
    recorder = Recorder()
    patcher = Patcher(recorder)
    col = Collection(str(Path(temp) / "sample.anki2"))
    try:
        patcher.install(discover([("anki", anki.hooks)]))
        patcher.recording = True
        note = col.new_note(col.models.current())
        note["Front"] = "Hello"
        note["Back"] = "World"
        col.add_note(note, col.decks.id("Default"))
        for event in recorder.snapshot():
            print(f"{event.seq}: {event.hook} {event.args}")
    finally:
        patcher.uninstall()
        col.close()
