from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtWidgets import QFileIconProvider
from PySide6.QtCore import QFileInfo
from typing import Any


class FileListModel(QAbstractListModel):
    """ファイルとディレクトリのリストを表示するためのモデルクラス"""
    def __init__(self, entries=None, parent=None):
        super().__init__(parent)
        self._entries = entries or []
        self._icon_provider = QFileIconProvider()

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        return len(self._entries)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        entry = self._entries[index.row()]
        name = entry["name"]
        is_dir = entry["is_dir"]
        path = entry.get("path")

        if role == Qt.ItemDataRole.DisplayRole:
            return f"{name}/" if is_dir else name

        if role == Qt.ItemDataRole.DecorationRole:
            if path:
                return self._icon_provider.icon(QFileInfo(path))
            if is_dir:
                return self._icon_provider.icon(QFileIconProvider.IconType.Folder)
            return self._icon_provider.icon(QFileIconProvider.IconType.File)

        return None

    def set_entries(self, entries):
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()

