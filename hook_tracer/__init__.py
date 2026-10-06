"""Anki add-on entry point. Plain Python imports do not load Qt or Anki."""

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aqt.main import AnkiQt

from .core.discovery import discover
from .core.patching import Patcher
from .core.recorder import Recorder, TraceEvent

_controller: "Controller | None" = None


class Controller:
    """One tracer per running Anki main window."""

    def __init__(self, mw: "AnkiQt") -> None:
        import anki.hooks
        from aqt import gui_hooks
        from aqt.qt import QAction, QTimer

        self.mw = mw
        self.recorder = Recorder()
        self.patcher = Patcher(self.recorder)
        self._timers: list[QTimer] = []
        self._last_seq: dict[QTimer, int] = {}
        self._stopped = False
        # Config is read before installation and before any later startup hooks fire.
        config = mw.addonManager.getConfig(__name__) or {}
        self.patcher.recording = config.get("trace_on_startup") is True
        try:
            self.patcher.install(discover([("anki", anki.hooks), ("gui", gui_hooks)]))
            with self.patcher.suppress():
                self.action = QAction("Hook Tracer: Record", mw)
                self.action.setCheckable(True)
                self.action.setChecked(self.patcher.recording)
                self.action.toggled.connect(self.set_recording)
                mw.form.menuTools.addAction(self.action)
                gui_hooks.debug_console_will_show.append(self._console_opened)
                mw.app.aboutToQuit.connect(self.stop)
        except BaseException:
            self.patcher.uninstall()
            raise

    def set_recording(self, value: bool) -> None:
        with self.patcher.suppress():
            self.patcher.recording = value

    def _console_opened(self, console: Any) -> None:
        """Temporary debug-console output until the phase 3 stream panel exists."""
        from aqt.qt import QTimer

        with self.patcher.suppress():
            timer = QTimer(console)
            self._timers.append(timer)
            # Show retained startup events as well as subsequent fires.
            self._last_seq[timer] = 0
            timer.timeout.connect(lambda: self._flush(console, timer))
            console.finished.connect(lambda *_: self._close_console(timer))
            timer.start(250)
            self._flush(console, timer)

    def _flush(self, console: Any, timer: Any) -> None:
        if self._stopped:
            return
        with self.patcher.suppress():
            events = self.recorder.since(self._last_seq[timer])
            for event in events:
                console._log.appendPlainText(format_event(event))
            if events:
                self._last_seq[timer] = events[-1].seq

    def _close_console(self, timer: Any) -> None:
        with self.patcher.suppress():
            timer.stop()
            if timer in self._timers:
                self._timers.remove(timer)
            self._last_seq.pop(timer, None)

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        with self.patcher.suppress():
            from aqt import gui_hooks

            for timer in list(self._timers):
                self._close_console(timer)
            gui_hooks.debug_console_will_show.remove(self._console_opened)
            self.mw.form.menuTools.removeAction(self.action)
            self.action.deleteLater()
            self.patcher.recording = False
            self.patcher.uninstall()
            self.mw.app.aboutToQuit.disconnect(self.stop)


def format_event(event: TraceEvent) -> str:
    return (
        f"[Hook Tracer] {event.t_ms:.1f} ms {event.hook} ({event.kind}) "
        f"{event.duration_ms:.2f} ms callbacks={len(event.callbacks)} "
        f"args={event.args} {event.error or ''}"
    )


def start(mw: "AnkiQt") -> Controller:
    global _controller
    if _controller is None or _controller._stopped:
        _controller = Controller(mw)
    return _controller


def stop() -> None:
    global _controller
    if _controller is not None:
        _controller.stop()
        _controller = None


# Anki imports add-ons after creating mw and the Tools menu. Avoid importing
# aqt in standalone headless tests and while Anki itself is still importing.
if "aqt" in sys.modules:
    from aqt import mw as _mw

    if _mw is not None:
        start(_mw)
