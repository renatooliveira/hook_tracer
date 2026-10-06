"""Transparent class-level generated dispatch wrappers."""

import functools
import inspect
from contextlib import contextmanager
from threading import Lock, local
from time import perf_counter_ns
from typing import Any, Callable, Iterator

from .discovery import HookInfo
from .recorder import Recorder


class Patcher:
    def __init__(self, recorder: Recorder):
        self.recorder = recorder
        self.recording = False
        self.muted: set[str] = set()
        self._originals: dict[type, Callable[..., Any]] = {}
        self._guard = local()
        self._count_lock = Lock()
        self._counts: dict[str, int] = {}

    def counts(self) -> dict[str, int]:
        """Counts eligible fires (including failing dispatches); buffer clear leaves them intact."""
        with self._count_lock:
            return self._counts.copy()

    @contextmanager
    def suppress(self) -> Iterator[None]:
        """Skip recording while tracer-owned UI or recorder work runs on this thread."""
        depth = getattr(self._guard, "depth", 0)
        self._guard.depth = depth + 1
        try:
            yield
        finally:
            self._guard.depth = depth

    def install(self, hooks: list[HookInfo]) -> None:
        for info in hooks:
            cls = type(info.instance)
            if cls in self._originals:
                continue
            original = cls.__call__
            wrapper = self._wrap(info, original)
            setattr(cls, "__call__", wrapper)
            self._originals[cls] = original

    def uninstall(self) -> None:
        for cls, original in self._originals.items():
            setattr(cls, "__call__", original)
        self._originals.clear()

    def _wrap(self, info: HookInfo, original: Callable[..., Any]) -> Callable[..., Any]:
        recorder = self.recorder
        first_param = None
        if info.kind == "filter":
            try:
                first_param = list(inspect.signature(original).parameters)[1]
            except (ValueError, IndexError):
                first_param = None

        @functools.wraps(original)
        def traced(instance: object, *args: Any, **kwargs: Any) -> Any:
            if (
                not self.recording
                or info.name in self.muted
                or getattr(self._guard, "depth", 0) > 0
            ):
                return original(instance, *args, **kwargs)
            started = perf_counter_ns()
            with self._count_lock:
                self._counts[info.name] = self._counts.get(info.name, 0) + 1
            callbacks: tuple[tuple[str, str], ...] = ()
            arg_text: tuple[str, ...] = ()
            input_value: object = None
            input_text: str | None = None
            with self.suppress():
                try:
                    callbacks = recorder.callback_names(tuple(getattr(instance, "_hooks")))
                    arg_text = recorder.arguments(args, kwargs)
                    if info.kind == "filter":
                        input_value = (
                            args[0] if args else kwargs.get(first_param) if first_param else None
                        )
                        if recorder.capture_args:
                            input_text = recorder.summary(input_value)
                except BaseException:
                    recorder.note_error()
            result: object = None
            error: BaseException | None = None
            try:
                result = original(instance, *args, **kwargs)
                return result
            except BaseException as exc:
                error = exc
                raise
            finally:
                ended = perf_counter_ns()
                with self.suppress():
                    try:
                        recorder.record(
                            hook=info.name,
                            kind=info.kind,
                            started_ns=started,
                            ended_ns=ended,
                            callbacks=callbacks,
                            args=arg_text,
                            filter_in=input_text,
                            result=result,
                            input_value=input_value,
                            error=error,
                        )
                    except BaseException:
                        recorder.note_error()

        return traced
