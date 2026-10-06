"""Thread-safe, bounded, Qt-free event storage and serialization."""

import reprlib
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock, current_thread
from time import perf_counter_ns
from typing import Any, Callable

from .discovery import Kind
from .owners import callback_owner


@dataclass(frozen=True)
class TraceEvent:
    seq: int
    t_ms: float
    hook: str
    kind: Kind
    thread: str
    duration_ms: float
    callbacks: tuple[tuple[str, str], ...]
    args: tuple[str, ...]
    filter_in: str | None
    filter_out: str | None
    changed: bool | None
    error: str | None


class _SafeRepr(reprlib.Repr):
    def __init__(self, on_error: Callable[[], None]):
        super().__init__()
        self.on_error = on_error

    def repr_instance(self, x: object, level: int) -> str:
        try:
            return (
                super().repr_instance(x, level)
                if type(x).__repr__ is object.__repr__
                else self._custom(x)
            )
        except Exception:
            self.on_error()
            return "<repr failed>"

    def _custom(self, x: object) -> str:
        return repr(x)[: self.maxother]


class Recorder:
    def __init__(
        self,
        buffer_size: int = 5000,
        capture_args: bool = True,
        repr_max_len: int = 200,
        add_on_names: Mapping[str, str] | None = None,
    ):
        if buffer_size < 1 or repr_max_len < 1:
            raise ValueError("buffer_size and repr_max_len must be positive")
        self.add_on_names = dict(add_on_names or {})
        self.capture_args = capture_args
        self.repr_max_len = repr_max_len
        self._events: deque[TraceEvent] = deque(maxlen=buffer_size)
        self._lock = Lock()
        self._seq = 0
        self._errors = 0
        self._start = perf_counter_ns()

    @property
    def recording_errors(self) -> int:
        with self._lock:
            return self._errors

    def note_error(self) -> None:
        with self._lock:
            self._errors += 1

    def summary(self, value: object) -> str:
        """Never leak an object's repr failure into dispatch."""
        try:
            rep = _SafeRepr(self.note_error)
            rep.maxstring = self.repr_max_len
            rep.maxother = self.repr_max_len
            text = rep.repr(value).replace("\r", "\\r").replace("\n", "\\n")
            return text[: self.repr_max_len]
        except Exception:
            self.note_error()
            return "<repr failed>"

    def arguments(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, ...]:
        if not self.capture_args:
            return ()
        return tuple(self.summary(arg) for arg in args) + tuple(
            f"{key}={self.summary(value)}" for key, value in kwargs.items()
        )

    def callback_names(self, callbacks: tuple[object, ...]) -> tuple[tuple[str, str], ...]:
        return tuple(callback_owner(callback, self.add_on_names) for callback in callbacks)

    def record(
        self,
        *,
        hook: str,
        kind: Kind,
        started_ns: int,
        ended_ns: int,
        callbacks: tuple[tuple[str, str], ...],
        args: tuple[str, ...],
        filter_in: str | None,
        result: object,
        input_value: object,
        error: BaseException | None,
    ) -> TraceEvent:
        output = (
            self.summary(result)
            if kind == "filter" and error is None and self.capture_args
            else None
        )
        changed: bool | None = None
        if kind == "filter" and error is None:
            try:
                changed = result is not input_value and bool(result != input_value)
            except Exception:
                self.note_error()
        error_text = (
            f"{type(error).__module__}.{type(error).__qualname__}: {self.summary(error)}"
            if error is not None
            else None
        )
        with self._lock:
            self._seq += 1
            event = TraceEvent(
                self._seq,
                (started_ns - self._start) / 1e6,
                hook,
                kind,
                current_thread().name,
                (ended_ns - started_ns) / 1e6,
                callbacks,
                args,
                filter_in,
                output,
                changed,
                error_text,
            )
            self._events.append(event)
        return event

    def since(self, seq: int) -> tuple[TraceEvent, ...]:
        with self._lock:
            return tuple(event for event in self._events if event.seq > seq)

    def snapshot(self) -> tuple[TraceEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def clear(self) -> None:
        """Discard buffered events; sequence numbers never restart."""
        with self._lock:
            self._events.clear()
