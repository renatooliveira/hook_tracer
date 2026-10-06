"""Integration with the pinned Anki pylib, no GUI or user profile."""

import anki.collection  # noqa: F401 - import before hooks (upstream import cycle)
import anki.hooks
from anki.collection import Collection

from hook_tracer.core.discovery import discover
from hook_tracer.core.patching import Patcher
from hook_tracer.core.recorder import Recorder


def test_add_note(tmp_path):
    recorder = Recorder()
    patcher = Patcher(recorder)
    col = Collection(str(tmp_path / "test.anki2"))
    try:
        patcher.install(discover([("anki", anki.hooks)]))
        patcher.recording = True
        note = col.new_note(col.models.current())
        note["Front"] = "phase one"
        note["Back"] = "trace"
        col.add_note(note, col.decks.id("Default"))
        names = {event.hook for event in recorder.snapshot()}
        assert "anki.note_will_be_added" in names
    finally:
        patcher.uninstall()
        col.close()


def test_real_registrations_and_attribution(tmp_path):
    recorder = Recorder()
    patcher = Patcher(recorder)
    hook = anki.hooks.note_will_be_added
    col = Collection(str(tmp_path / "registrations.anki2"))

    def listener(*args):
        pass

    listener.__module__ = "anki.custom"
    hook.append(listener)
    try:
        patcher.install(discover([("anki", anki.hooks)]))
        patcher.recording = True
        for n in range(2):
            if n:
                hook.remove(listener)
            note = col.new_note(col.models.current())
            note["Front"] = f"note {n}"
            note["Back"] = "back"
            col.add_note(note, col.decks.id("Default"))
        events = [e for e in recorder.snapshot() if e.hook == "anki.note_will_be_added"]
        assert len(events) == 2
        assert events[0].callbacks == (
            ("anki.custom.test_real_registrations_and_attribution.<locals>.listener", "core"),
        )
        assert events[1].callbacks == ()
        assert patcher.counts()["anki.note_will_be_added"] == 2
    finally:
        hook.remove(listener)
        patcher.uninstall()
        col.close()
