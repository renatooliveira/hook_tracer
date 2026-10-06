"""Attribution, lifetime counts, and live-registration behavior."""

from functools import partial
from threading import Thread

from hook_tracer.core.discovery import discover
from hook_tracer.core.owners import add_on_names, callback_owner
from hook_tracer.core.patching import Patcher
from hook_tracer.core.recorder import Recorder
from tests import fake_hooks as fake


def test_owner_unwrap_and_unusual_objects():
    class Handler:
        def handler(self, value):
            pass

        def __call__(self, value):
            pass

    Handler.__module__ = "demo_addon.handlers"
    Handler.handler.__module__ = "demo_addon.handlers"
    Handler.__call__.__module__ = "demo_addon.handlers"
    handler = Handler()
    names = {"demo_addon": "Helpful Add-on"}
    expected = (
        f"demo_addon.handlers.{Handler.handler.__qualname__}",
        "Helpful Add-on (demo_addon)",
    )
    assert callback_owner(handler.handler, names) == expected
    assert callback_owner(partial(partial(handler.handler)), names) == expected
    assert callback_owner(handler, names) == (
        f"demo_addon.handlers.{Handler.__call__.__qualname__}",
        "Helpful Add-on (demo_addon)",
    )
    assert callback_owner(len, names)[1] == "unknown"
    assert callback_owner(fake.did_something.append, names)[1] == "unknown"

    class Bad:
        def __getattribute__(self, name):
            raise RuntimeError("broken")

    assert callback_owner(Bad(), names) == ("<callback unknown>", "unknown")
    assert callback_owner(partial(len), names)[1] == "unknown"
    from anki.collection import Collection

    assert callback_owner(Collection.close, names)[1] == "core"
    assert add_on_names(["demo_addon", "broken"], lambda folder: names[folder]) == {
        "demo_addon": "Helpful Add-on",
        "broken": "broken",
    }


def test_ownership_frozen_at_fire_and_session_counts():
    fake._DidSomethingHook._hooks = []
    fake.legacy_calls.clear()
    recorder = Recorder(buffer_size=1, add_on_names={"demo_addon": "Demo"})
    patcher = Patcher(recorder)

    def callback(value):
        pass

    callback.__module__ = "demo_addon.handlers"
    fake.did_something.append(callback)
    patcher.install(discover([("anki", fake)]))
    try:
        patcher.recording = True
        fake.did_something("one")
        event = recorder.snapshot()[0]
        assert event.callbacks == (
            (
                "demo_addon.handlers.test_ownership_frozen_at_fire_and_session_counts.<locals>.callback",
                "Demo (demo_addon)",
            ),
        )
        fake.did_something.remove(callback)
        assert event.callbacks == recorder.snapshot()[0].callbacks
        fake.did_something("two")
        assert len(recorder.snapshot()) == 1
        assert patcher.counts()["anki.did_something"] == 2
        recorder.clear()
        assert patcher.counts()["anki.did_something"] == 2
        patcher.recording = False
        fake.did_something("paused")
        patcher.recording = True
        patcher.muted.add("anki.did_something")
        fake.did_something("muted")
        assert patcher.counts()["anki.did_something"] == 2
        patcher.muted.clear()
        with patcher.suppress():
            fake.did_something("guarded")
        assert patcher.counts()["anki.did_something"] == 2
        threads = [Thread(target=lambda: fake.did_something("thread")) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert patcher.counts()["anki.did_something"] == 12
    finally:
        patcher.uninstall()
        fake._DidSomethingHook._hooks = []
