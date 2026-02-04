import os

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    Qt,
)
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPolygon
from PySide6.QtWidgets import QFileIconProvider
from typing import Any

from image.loader import ImageLoader


class FileListModel(QAbstractListModel):
    """ファイルとディレクトリのリストを表示するためのモデルクラス"""
    def __init__(self, entries=None, parent=None):
        super().__init__(parent)
        self._entries = entries or []
        self._icon_provider = QFileIconProvider()
        self._image_icon = self._create_image_icon()

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex = QModelIndex(),
    ) -> int:
        return len(self._entries)

    @staticmethod
    def _create_image_icon() -> QIcon:
        """画像ファイル用のアイコンを生成する"""
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 外枠
        painter.setBrush(QColor(200, 220, 255))
        painter.setPen(QColor(100, 130, 180))
        painter.drawRoundedRect(2, 2, size - 4, size - 4, 3, 3)

        # 山のシルエット
        painter.setBrush(QColor(80, 160, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygon([
            QPoint(4, 26), QPoint(12, 12), QPoint(18, 18),
            QPoint(24, 10), QPoint(28, 26),
        ]))

        # 太陽
        painter.setBrush(QColor(255, 200, 50))
        painter.drawEllipse(6, 6, 8, 8)

        painter.end()
        return QIcon(pixmap)

    def _is_image_file(self, name: str) -> bool:
        """ImageLoaderが対応している画像ファイルかどうか判定する"""
        ext = os.path.splitext(name)[1].lower()
        return ext in ImageLoader.EXTENSIONS

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

        if role == Qt.ItemDataRole.DisplayRole:
            return f"{name}/" if is_dir else name

        if role == Qt.ItemDataRole.DecorationRole:
            if is_dir:
                return self._icon_provider.icon(QFileIconProvider.IconType.Folder)
            if self._is_image_file(name):
                return self._image_icon
            return self._icon_provider.icon(QFileIconProvider.IconType.File)

        return None

    def set_entries(self, entries):
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()

