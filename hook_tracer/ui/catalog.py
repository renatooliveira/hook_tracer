"""Current generated-hook registrations and lifetime recorded-fire counts."""

from aqt.qt import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, QTableView

from hook_tracer.core.discovery import HookInfo
from hook_tracer.core.patching import Patcher
from hook_tracer.core.recorder import Recorder

HEADERS = ("Hook", "Kind", "Fires", "Callbacks", "Owners")
CatalogRow = tuple[str, str, int, int, str]


class CatalogModel(QAbstractTableModel):
    def __init__(self, hooks: list[HookInfo], patcher: Patcher, recorder: Recorder) -> None:
        super().__init__()
        self.hooks = hooks
        self.patcher = patcher
        self.recorder = recorder
        self.rows: list[CatalogRow] = []
        self.refresh()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(HEADERS)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return HEADERS[section] if 0 <= section < len(HEADERS) else None
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | int | None:
        if not index.isValid() or index.row() >= len(self.rows) or index.column() >= len(HEADERS):
            return None
        value = self.rows[index.row()][index.column()]
        if role == Qt.ItemDataRole.UserRole:
            return value
        if role == Qt.ItemDataRole.DisplayRole:
            return str(value)
        return None

    def refresh(self) -> None:
        counts = self.patcher.counts()
        rows: list[CatalogRow] = []
        for info in self.hooks:
            try:
                callbacks = tuple(getattr(info.instance, "_hooks"))
                owners = sorted({owner for _, owner in self.recorder.callback_names(callbacks)})
                rows.append(
                    (
                        info.name,
                        info.kind,
                        counts.get(info.name, 0),
                        len(callbacks),
                        ", ".join(owners),
                    )
                )
            except Exception:
                self.recorder.note_error()
                rows.append((info.name, info.kind, counts.get(info.name, 0), 0, "unknown"))
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


def catalog_table(
    hooks: list[HookInfo], patcher: Patcher, recorder: Recorder
) -> tuple[QTableView, CatalogModel]:
    model = CatalogModel(hooks, patcher, recorder)
    table = QTableView()
    proxy = QSortFilterProxyModel(table)
    proxy.setSourceModel(model)
    proxy.setSortRole(Qt.ItemDataRole.UserRole)
    table.setModel(proxy)
    table.setSortingEnabled(True)
    table.sortByColumn(3, Qt.SortOrder.DescendingOrder)
    return table, model
