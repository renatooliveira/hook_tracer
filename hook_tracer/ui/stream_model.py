"""Main-thread table projection of the bounded recorder snapshot."""

import re
from threading import main_thread

from aqt.qt import QAbstractTableModel, QColor, QModelIndex, Qt

from hook_tracer.core.recorder import Recorder, TraceEvent

COLUMNS = ("Time", "Hook", "Kind", "Thread", "Duration (ms)", "Callbacks", "Args")


class StreamModel(QAbstractTableModel):
    def __init__(self, recorder: Recorder) -> None:
        super().__init__()
        self.recorder = recorder
        self._rows: list[TraceEvent] = []
        self._last_seq = 0
        self.query = ""
        self.regex = False
        self.hide_empty = False
        self.filter_error: str | None = None
        self._pattern: re.Pattern[str] | None = None
        self._main_thread = main_thread().name

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section] if 0 <= section < len(COLUMNS) else None
        return None

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> str | QColor | None:
        if not index.isValid() or index.row() >= len(self._rows) or index.column() >= len(COLUMNS):
            return None
        event = self._rows[index.row()]
        if role == Qt.ItemDataRole.BackgroundRole and event.thread != self._main_thread:
            return QColor("#ffe7a8")
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        return (
            f"{event.t_ms:.1f}",
            event.hook,
            event.kind,
            event.thread,
            f"{event.duration_ms:.2f}",
            str(len(event.callbacks)),
            " ".join(event.args),
        )[index.column()]

    def event_at(self, row: int) -> TraceEvent | None:
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def set_filters(self, query: str, regex: bool, hide_empty: bool) -> None:
        self.query, self.regex, self.hide_empty = query, regex, hide_empty
        self.filter_error = None
        self._pattern = None
        if regex and query:
            try:
                self._pattern = re.compile(query, re.IGNORECASE)
            except re.error as exc:
                self.filter_error = str(exc)
        self.reload()

    def _matches(self, event: TraceEvent) -> bool:
        if self.hide_empty and not event.callbacks:
            return False
        if self.filter_error:
            return False
        if self.regex:
            return not self._pattern or bool(self._pattern.search(event.hook))
        return self.query.casefold() in event.hook.casefold()

    def reload(self) -> None:
        """Rebuild from the current bounded snapshot after clear or filter changes."""
        events = self.recorder.snapshot()
        self.beginResetModel()
        self._rows = [event for event in events if self._matches(event)]
        self._last_seq = events[-1].seq if events else self._last_seq
        self.endResetModel()

    def refresh(self) -> None:
        """Append new fires, discarding rows evicted or cleared since the last tick."""
        events = self.recorder.snapshot()
        oldest = events[0].seq if events else None
        # Rows are in sequence order, including when a filtered view skipped events.
        expired = 0
        while expired < len(self._rows) and (oldest is None or self._rows[expired].seq < oldest):
            expired += 1
        if expired:
            self.beginRemoveRows(QModelIndex(), 0, expired - 1)
            del self._rows[:expired]
            self.endRemoveRows()
        fresh = [event for event in events if event.seq > self._last_seq]
        if fresh:
            self._last_seq = fresh[-1].seq
            matching = [event for event in fresh if self._matches(event)]
            if matching:
                start = len(self._rows)
                self.beginInsertRows(QModelIndex(), start, start + len(matching) - 1)
                self._rows.extend(matching)
                self.endInsertRows()
