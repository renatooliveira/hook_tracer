"""Configuration validation and atomic snapshot export."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from hook_tracer.core.config import Config, validate
from hook_tracer.core.export import export_jsonl
from hook_tracer.core.recorder import Recorder


def test_config_defaults_and_types():
    assert validate({}) == (Config(), ())
    config, warnings = validate(
        {
            "trace_on_startup": True,
            "buffer_size": 12,
            "capture_args": False,
            "repr_max_len": 50,
            "muted_hooks": ["gui.media_sync_did_progress", "gui.media_sync_did_progress"],
        }
    )
    assert config == Config(True, 12, False, 50, ("gui.media_sync_did_progress",))
    assert warnings == ()
    config, warnings = validate(
        {
            "trace_on_startup": 1,
            "buffer_size": True,
            "capture_args": "false",
            "repr_max_len": -1,
            "muted_hooks": [123],
            "trace_legacy": True,
        }
    )
    assert config == Config()
    assert len(warnings) == 6
    assert "unsupported" in warnings[-1]
    assert validate({"trace_legacy": "true"})[0].trace_legacy is False
    assert validate([])[0] == Config()
    assert validate({"buffer_size": 100_001, "repr_max_len": 10_001})[0] == Config()


def test_export_snapshot_even_after_eviction_and_clear(tmp_path: Path):
    recorder = Recorder(buffer_size=2)
    for hook in ("anki.first", "anki.second", "anki.third"):
        recorder.record(
            hook=hook,
            kind="hook",
            started_ns=1,
            ended_ns=2,
            callbacks=(("callback", "add-on"),),
            args=("content\nsecret",),
            filter_in=None,
            result=None,
            input_value=None,
            error=None,
        )
    snapshot = recorder.snapshot()
    recorder.clear()
    path = tmp_path / "trace.jsonl"
    export_jsonl(path, snapshot)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["seq"] for row in rows] == [2, 3]
    assert rows[0]["args"] == ["content\nsecret"]
    assert set(rows[0]) == set(asdict(snapshot[0]))
    assert tuple(rows[0]["callbacks"][0]) == snapshot[0].callbacks[0]
    assert not list(tmp_path.glob("*.tmp"))


def test_export_failure_preserves_destination_and_removes_temporary_file(tmp_path: Path):
    path = tmp_path / "trace.jsonl"
    path.write_text("previous")

    class Bad:
        def __iter__(self):
            yield object()  # asdict cannot serialize this as an event

    with pytest.raises(TypeError):
        export_jsonl(path, Bad())  # type: ignore[arg-type]
    assert path.read_text() == "previous"
    assert sorted(tmp_path.iterdir()) == [path]
