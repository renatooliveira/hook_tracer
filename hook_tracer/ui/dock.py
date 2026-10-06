"""Live stream dock; all widget access is confined to Anki's main thread."""

from collections.abc import Callable

from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QTimer,
    QVBoxLayout,
    QWidget,
)

from hook_tracer.core.patching import Patcher
from hook_tracer.core.recorder import Recorder

from .stream_model import StreamModel


class StreamDock(QDockWidget):
    def __init__(
        self,
        mw: QWidget,
        patcher: Patcher,
        recorder: Recorder,
        on_recording: Callable[[bool], None],
    ) -> None:
        super().__init__("Hook Tracer", mw)
        self.patcher = patcher
        self.recorder = recorder
        self.on_recording = on_recording
        self.model = StreamModel(recorder)
        self.setObjectName("HookTracerDock")
        content = QWidget(self)
        layout = QVBoxLayout(content)
        controls = QHBoxLayout()
        self.pause = QPushButton(content)
        self.pause.clicked.connect(self._toggle_recording)
        self.clear = QPushButton("Clear", content)
        self.clear.clicked.connect(self._clear)
        self.search = QLineEdit(content)
        self.search.setPlaceholderText("Hook name")
        self.search.textChanged.connect(self._filter_changed)
        self.regex = QCheckBox("Regex", content)
        self.regex.toggled.connect(self._filter_changed)
        self.hide_empty = QCheckBox("Hide no callbacks", content)
        self.hide_empty.toggled.connect(self._filter_changed)
        for widget in (self.pause, self.clear, self.search, self.regex, self.hide_empty):
            controls.addWidget(widget)
        layout.addLayout(controls)
        self.filter_message = QLabel(content)
        layout.addWidget(self.filter_message)
        self.table = QTableView(content)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        mute_controls = QHBoxLayout()
        self.mute = QPushButton("Mute recording for selected hook", content)
        self.mute.clicked.connect(self._mute_selected)
        self.muted = QComboBox(content)
        self.unmute = QPushButton("Unmute selected", content)
        self.unmute.clicked.connect(self._unmute_selected)
        mute_controls.addWidget(self.mute)
        mute_controls.addWidget(QLabel("Session mutes:", content))
        mute_controls.addWidget(self.muted)
        mute_controls.addWidget(self.unmute)
        layout.addLayout(mute_controls)
        self.setWidget(content)
        self._sync_recording()
        self._sync_mutes()
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.refresh)
        self.visibilityChanged.connect(self._visibility_changed)

    def _sync_recording(self) -> None:
        self.pause.setText("Pause" if self.patcher.recording else "Resume")

    def _sync_mutes(self) -> None:
        previous = self.muted.currentText()
        self.muted.clear()
        self.muted.addItems(sorted(self.patcher.muted))
        if previous in self.patcher.muted:
            self.muted.setCurrentText(previous)
        self.unmute.setEnabled(bool(self.patcher.muted))

    def _visibility_changed(self, visible: bool) -> None:
        with self.patcher.suppress():
            if visible:
                self.refresh()
                self.timer.start()
            else:
                self.timer.stop()

    def refresh(self) -> None:
        with self.patcher.suppress():
            self.model.refresh()
            self._sync_recording()
            if set(self.muted.itemText(i) for i in range(self.muted.count())) != self.patcher.muted:
                self._sync_mutes()

    def _filter_changed(self, *_: object) -> None:
        with self.patcher.suppress():
            self.model.set_filters(
                self.search.text(), self.regex.isChecked(), self.hide_empty.isChecked()
            )
            self.filter_message.setText(
                f"Invalid regex: {self.model.filter_error}" if self.model.filter_error else ""
            )

    def _toggle_recording(self) -> None:
        with self.patcher.suppress():
            self.on_recording(not self.patcher.recording)
            self._sync_recording()

    def _clear(self) -> None:
        with self.patcher.suppress():
            self.recorder.clear()
            self.model.reload()

    def _mute_selected(self) -> None:
        with self.patcher.suppress():
            event = self.model.event_at(self.table.currentIndex().row())
            if event is not None:
                self.patcher.muted.add(event.hook)
                self._sync_mutes()

    def _unmute_selected(self) -> None:
        with self.patcher.suppress():
            self.patcher.muted.discard(self.muted.currentText())
            self._sync_mutes()

    def shutdown(self) -> None:
        self.timer.stop()
        self.hide()
        self.deleteLater()
