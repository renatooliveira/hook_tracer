"""Headless behavioral and failure-path tests."""

import gc
import timeit
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from types import ModuleType

import pytest

from hook_tracer.core.discovery import discover
from hook_tracer.core.patching import Patcher
from hook_tracer.core.recorder import Recorder
from tests import fake_hooks as fake


@pytest.fixture
def setup():
    fake._DidSomethingHook._hooks = []
    fake._TransformFilter._hooks = []
    fake.legacy_calls.clear()
    recorder = Recorder()
    patcher = Patcher(recorder)
    info = discover([("anki", fake)])
    patcher.install(info)
    patcher.recording = True
    yield recorder, patcher
    patcher.uninstall()
    fake._DidSomethingHook._hooks = []
    fake._TransformFilter._hooks = []


def test_discovery():
    other = ModuleType("other")
    other.reexport = fake.did_something
    other.bogus = object()
    assert [(i.name, i.kind) for i in discover([("anki", fake), ("gui", other)])] == [
        ("anki.did_something", "hook"),
        ("anki.transform", "filter"),
    ]


def test_fires_filters_snapshots_and_nesting(setup):
    recorder, patcher = setup
    fake.did_something.append(lambda value: fake.transform(value, "!"))
    fake.transform.append(lambda value, suffix: value + suffix)
    fake.did_something("hi")
    events = recorder.snapshot()
    assert [e.hook for e in events] == ["anki.transform", "anki.did_something"]
    assert events[0].filter_in == "'hi'"
    assert events[0].filter_out == "'hi!'"
    assert events[0].changed is True
    assert len(events[1].callbacks) == 1
    assert fake.legacy_calls == ["hi"]
    patcher.muted.add("anki.did_something")
    fake.did_something("muted")
    assert len(recorder.snapshot()) == 3  # nested filter still fires
    patcher.recording = False
    fake.did_something("paused")
    assert len(recorder.snapshot()) == 3
    with patcher.suppress():
        with patcher.suppress():
            patcher.recording = True
            fake.did_something("guarded")
    assert len(recorder.snapshot()) == 3


def test_failure_preserves_exception_and_removal(setup):
    recorder, patcher = setup
    exc = ValueError("original")

    def fail(value):
        raise exc

    fake.did_something.append(fail)
    with pytest.raises(ValueError) as caught:
        fake.did_something("x")
    assert caught.value is exc
    assert fake.did_something.count() == 0
    event = recorder.snapshot()[0]
    assert len(event.callbacks) == 1
    assert "ValueError" in (event.error or "")
    assert event.args == ("'x'",)
    assert fake.legacy_calls == []
    fake.did_something("next")
    assert len(recorder.snapshot()) == 2  # guard cleaned up


def test_recorder_failure_does_not_change_dispatch(setup, monkeypatch):
    recorder, _ = setup

    def broken(**kwargs):
        raise RuntimeError("recorder failed")

    monkeypatch.setattr(recorder, "record", broken)
    fake.transform.append(lambda value, suffix: value + suffix)
    assert fake.transform("a", "b") == "ab"
    assert recorder.recording_errors == 1
    exc = ValueError("callback")

    def fail(value):
        raise exc

    fake.did_something.append(fail)
    with pytest.raises(ValueError) as caught:
        fake.did_something()
    assert caught.value is exc
    assert recorder.recording_errors == 2


def test_eviction_clear_and_immutable_events(setup):
    _, patcher = setup
    recorder = Recorder(buffer_size=2)
    patcher.uninstall()
    patcher = Patcher(recorder)
    patcher.install(discover([("anki", fake)]))
    patcher.recording = True
    try:
        for n in range(3):
            fake.did_something(n)
        assert [e.seq for e in recorder.snapshot()] == [2, 3]
        assert [e.seq for e in recorder.since(2)] == [3]
        with pytest.raises(FrozenInstanceError):
            recorder.snapshot()[0].hook = "changed"
        recorder.clear()
        assert recorder.since(0) == ()
        fake.did_something(4)
        assert recorder.snapshot()[0].seq == 4
    finally:
        patcher.uninstall()


def test_serialization_non_retention_and_bad_objects(setup):
    recorder, _ = setup

    class Payload:
        def __repr__(self):
            raise ValueError("bad repr")

    value = Payload()
    ref = weakref.ref(value)
    fake.did_something(value)
    fake.legacy_calls.clear()
    del value
    gc.collect()
    assert ref() is None
    assert recorder.snapshot()[0].args == ("<repr failed>",)
    assert recorder.recording_errors == 1
    assert Recorder(capture_args=False).arguments((Payload(),), {}) == ()
    assert len(Recorder(repr_max_len=8).summary("a" * 100)) <= 8


def test_filter_identity_and_bad_comparison(setup):
    recorder, _ = setup
    value = []
    assert fake.transform(value) is value
    assert recorder.snapshot()[-1].changed is False

    class BadCompare:
        def __ne__(self, other):
            raise ValueError("compare")

    fake.transform.append(lambda value, suffix: BadCompare())
    fake.transform("x")
    assert recorder.snapshot()[-1].changed is None
    assert recorder.recording_errors == 1


def test_filter_keyword_input_and_failure(setup):
    recorder, _ = setup
    fake.transform.append(lambda value, suffix: value + suffix)
    assert fake.transform(value="a", suffix="b") == "ab"
    assert recorder.snapshot()[-1].filter_in == "'a'"
    assert recorder.snapshot()[-1].filter_out == "'ab'"
    exc = RuntimeError("filter failed")

    def fail(value, suffix):
        raise exc

    fake.transform.append(fail)
    with pytest.raises(RuntimeError) as caught:
        fake.transform("x")
    assert caught.value is exc
    assert fake.transform.count() == 1
    event = recorder.snapshot()[-1]
    assert event.filter_out is None
    assert event.changed is None
    assert len(event.callbacks) == 2


def test_repr_reentrancy_and_disabled_capture(setup):
    recorder, _ = setup

    class Reentrant:
        def __repr__(self):
            fake.did_something("from repr")
            return "<reentrant>"

    fake.transform(Reentrant())
    assert len(recorder.snapshot()) == 1
    assert fake.legacy_calls and set(fake.legacy_calls) == {"from repr"}
    recorder.capture_args = False
    fake.transform("secret")
    event = recorder.snapshot()[-1]
    assert event.args == ()
    assert event.filter_in is None and event.filter_out is None
    assert event.changed is False  # identity comparison still recorded


def test_threads(setup):
    recorder, _ = setup
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="worker") as pool:
        list(pool.map(fake.did_something, range(100)))
    events = recorder.snapshot()
    assert len(events) == 100
    assert sorted(e.seq for e in events) == list(range(1, 101))
    assert all(e.thread.startswith("worker") for e in events)


def test_idempotent_install_restore_and_paused_benchmark(setup):
    _, patcher = setup
    patcher.uninstall()
    original = fake._DidSomethingHook.__call__
    info = discover([("anki", fake)])
    baseline = timeit.timeit(lambda: fake.did_something(None), number=10000)
    patcher.install(info)
    wrapped = fake._DidSomethingHook.__call__
    patcher.install(info)
    assert fake._DidSomethingHook.__call__ is wrapped
    patcher.recording = False
    paused = timeit.timeit(lambda: fake.did_something(None), number=10000)
    assert paused < max(0.5, baseline * 20)
    patcher.uninstall()
    assert fake._DidSomethingHook.__call__ is original
    patcher.install(info)
    patcher.uninstall()
    assert fake._DidSomethingHook.__call__ is original
