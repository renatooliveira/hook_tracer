"""Live stream dock; all widget access is confined to Anki's main thread."""

from collections.abc import Callable
from pathlib import Path

from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    Qt,
    QTableView,
    QTabWidget,
    QTimer,
    QVBoxLayout,
    QWidget,
)

from hook_tracer.core.discovery import HookInfo
from hook_tracer.core.export import export_jsonl
from hook_tracer.core.patching import Patcher
from hook_tracer.core.recorder import Recorder

from .catalog import catalog_table
from .detail import DetailPane
from .stream_model import StreamModel


class StreamDock(QDockWidget):
    def __init__(
        self,
        mw: QWidget,
        patcher: Patcher,
        recorder: Recorder,
        on_recording: Callable[[bool], None],
        hooks: list[HookInfo] | None = None,
        persist_mutes: Callable[[set[str]], None] | None = None,
        config_warnings: tuple[str, ...] = (),
    ) -> None:
        super().__init__("Hook Tracer", mw)
        self.patcher = patcher
        self.recorder = recorder
        self.on_recording = on_recording
        self.persist_mutes = persist_mutes
        self._saved_mutes = frozenset(patcher.muted)
        self.model = StreamModel(recorder)
        self.setObjectName("HookTracerDock")
        self.tabs = QTabWidget(self)
        content = QWidget(self.tabs)
        layout = QVBoxLayout(content)
        controls = QHBoxLayout()
        self.record_button = QPushButton(content)
        self.record_button.clicked.connect(self._toggle_recording)
        self.clear = QPushButton("Clear", content)
        self.clear.clicked.connect(self._clear)
        self.search = QLineEdit(content)
        self.search.setPlaceholderText("Hook name")
        self.search.textChanged.connect(self._filter_changed)
        self.regex = QCheckBox("Regex", content)
        self.regex.toggled.connect(self._filter_changed)
        self.hide_empty = QCheckBox("Hide no callbacks", content)
        self.hide_empty.toggled.connect(self._filter_changed)
        for widget in (self.record_button, self.clear, self.search, self.regex, self.hide_empty):
            controls.addWidget(widget)
        layout.addLayout(controls)
        self.filter_message = QLabel(content)
        layout.addWidget(self.filter_message)
        if config_warnings:
            layout.addWidget(QLabel("Config: " + "; ".join(config_warnings), content))
        self.table = QTableView(content)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.detail = DetailPane(recorder.capture_args)
        self._selected_seq: int | None = None
        selection = self.table.selectionModel()
        assert selection is not None
        selection.selectionChanged.connect(self._selection_changed)
        splitter = QSplitter(Qt.Orientation.Vertical, content)
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        layout.addWidget(splitter)
        mute_controls = QHBoxLayout()
        self.mute = QPushButton("Mute recording for selected hook", content)
        self.mute.clicked.connect(self._mute_selected)
        self.muted = QComboBox(content)
        self.unmute = QPushButton("Unmute selected", content)
        self.unmute.clicked.connect(self._unmute_selected)
        self.save_mutes = QPushButton("Save mutes as default", content)
        self.save_mutes.setEnabled(persist_mutes is not None)
        self.save_mutes.clicked.connect(self._persist_mutes)
        mute_controls.addWidget(self.mute)
        mute_controls.addWidget(QLabel("Session mutes:", content))
        mute_controls.addWidget(self.muted)
        mute_controls.addWidget(self.unmute)
        mute_controls.addWidget(self.save_mutes)
        layout.addLayout(mute_controls)
        self.mute_status = QLabel(content)
        layout.addWidget(self.mute_status)
        footer = QHBoxLayout()
        self.errors = QLabel("Recording errors: 0", content)
        self.export = QPushButton("Export JSON Lines…", content)
        self.export.clicked.connect(self._export)
        footer.addWidget(self.errors)
        footer.addWidget(self.export)
        layout.addLayout(footer)
        self.tabs.addTab(content, "Stream")
        self.catalog_table, self.catalog_model = catalog_table(hooks or [], patcher, recorder)
        self.tabs.addTab(self.catalog_table, "Catalog")
        self.tabs.currentChanged.connect(self._tab_changed)
        self.setWidget(self.tabs)
        self._ticks = 0
        self._sync_recording()
        self._sync_mutes()
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.refresh)
        self.visibilityChanged.connect(self._visibility_changed)

    def _sync_recording(self) -> None:
        self.record_button.setText(
            "Stop recording" if self.patcher.recording else "Start recording"
        )

    def _sync_mutes(self) -> None:
        previous = self.muted.currentText()
        self.muted.clear()
        self.muted.addItems(sorted(self.patcher.muted))
        if previous in self.patcher.muted:
            self.muted.setCurrentText(previous)
        self.unmute.setEnabled(bool(self.patcher.muted))
        self.mute_status.setText(
            "Session mute changes are not saved"
            if frozenset(self.patcher.muted) != self._saved_mutes
            else "Mutes match saved defaults"
        )

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
            if self._selected_seq is not None and not any(
                event.seq == self._selected_seq for event in self.model._rows
            ):
                self.table.clearSelection()
                self.detail.show_event(None)
                self._selected_seq = None
            self._ticks += 1
            if self.tabs.currentIndex() == 1 and self._ticks % 4 == 0:
                self.catalog_model.refresh()
            self._sync_recording()
            self.errors.setText(f"Recording errors: {self.recorder.recording_errors}")
            if set(self.muted.itemText(i) for i in range(self.muted.count())) != self.patcher.muted:
                self._sync_mutes()

    def _tab_changed(self, index: int) -> None:
        with self.patcher.suppress():
            if index == 1:
                self.catalog_model.refresh()

    def _selection_changed(self, *_: object) -> None:
        with self.patcher.suppress():
            selection = self.table.selectionModel()
            indexes = selection.selectedRows() if selection else []
            event = self.model.event_at(indexes[0].row()) if indexes else None
            self._selected_seq = event.seq if event else None
            self.detail.show_event(event)

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
            self._selected_seq = None
            self.detail.show_event(None)

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

    def _persist_mutes(self) -> None:
        with self.patcher.suppress():
            if self.persist_mutes is None:
                return
            try:
                self.persist_mutes(set(self.patcher.muted))
                self._saved_mutes = frozenset(self.patcher.muted)
                self._sync_mutes()
            except Exception as exc:
                QMessageBox.warning(self, "Hook Tracer", f"Could not save mutes: {exc}")

    def _export(self) -> None:
        with self.patcher.suppress():
            answer = QMessageBox.question(
                self,
                "Export trace?",
                "Argument summaries may contain card or note content. Export the entire "
                "current buffer (including hidden rows) to a local JSON Lines file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Hook Tracer events", "hook-trace.jsonl", "JSON Lines (*.jsonl)"
            )
            if not filename:
                return
            try:
                export_jsonl(Path(filename), self.recorder.snapshot())
            except Exception as exc:
                QMessageBox.warning(self, "Hook Tracer", f"Could not export trace: {exc}")

    def shutdown(self) -> None:
        self.timer.stop()
        self.hide()
        self.deleteLater()
