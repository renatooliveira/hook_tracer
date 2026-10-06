"""Anki add-on entry point. Plain Python imports do not load Qt or Anki."""

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aqt.main import AnkiQt

from .core.config import validate
from .core.discovery import discover
from .core.owners import add_on_names
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
        manager = mw.addonManager
        folders: list[str] = getattr(manager, "allAddons", lambda: [])()
        # Read config before installation, while startup hooks are still untouched.
        raw_config = manager.getConfig(__name__)
        self.config, self.config_warnings = validate(raw_config if raw_config is not None else {})
        self.recorder = Recorder(
            buffer_size=self.config.buffer_size,
            capture_args=self.config.capture_args,
            repr_max_len=self.config.repr_max_len,
            add_on_names=add_on_names(folders, manager.addonName) if folders else {},
        )
        self.patcher = Patcher(self.recorder)
        self.patcher.muted.update(self.config.muted_hooks)
        for warning in self.config_warnings:
            print(f"[Hook Tracer config] {warning}")
        self._timers: list[QTimer] = []
        self._last_seq: dict[QTimer, int] = {}
        self._stopped = False
        self._dock: Any = None
        self.patcher.recording = self.config.trace_on_startup
        try:
            self.hooks = discover([("anki", anki.hooks), ("gui", gui_hooks)])
            self.patcher.install(self.hooks)
            with self.patcher.suppress():
                self.open_action = QAction("Hook Tracer", mw)
                self.open_action.triggered.connect(self.open_panel)
                mw.form.menuTools.addAction(self.open_action)
                gui_hooks.debug_console_will_show.append(self._console_opened)
                mw.app.aboutToQuit.connect(self.stop)
        except BaseException:
            self.patcher.uninstall()
            raise

    def set_recording(self, value: bool) -> None:
        with self.patcher.suppress():
            self.patcher.recording = value

    def open_panel(self) -> None:
        from aqt.qt import Qt

        from .ui.dock import StreamDock

        with self.patcher.suppress():
            if self._dock is None:
                self._dock = StreamDock(
                    self.mw,
                    self.patcher,
                    self.recorder,
                    self.set_recording,
                    self.hooks,
                    self.persist_mutes,
                    self.config_warnings,
                )
                self.mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._dock)
            self._dock.show()
            self._dock.raise_()

    def persist_mutes(self, names: set[str]) -> None:
        """Save only an explicit user choice, preserving other add-on settings."""
        manager = self.mw.addonManager
        current = manager.getConfig(__name__)
        config = dict(current) if isinstance(current, dict) else {}
        config["muted_hooks"] = sorted(names)
        manager.writeConfig(__name__, config)

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
            if self._dock is not None:
                self._dock.shutdown()
                self._dock = None
            self.mw.form.menuTools.removeAction(self.open_action)
            self.open_action.deleteLater()
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
