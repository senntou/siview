import os

from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt
# PyQt5の場合は import を置き換えるだけ


class ImageLoader:
    def __init__(self, return_pixmap: bool = False):
        """
        return_pixmap=True にすると QPixmap を返す
        False の場合は QImage
        """
        self.return_pixmap = return_pixmap

    def load(self, data: bytes, filename: str):
        ext = os.path.splitext(filename)[1].lower()

        if ext in [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif"]:
            image = QImage.fromData(data)
            if image.isNull():
                raise ValueError("画像の読み込みに失敗")

        elif ext == ".svg":
            image = self._load_svg(data)

        else:
            raise ValueError(f"未対応の拡張子: {ext}")

        if self.return_pixmap:
            return QPixmap.fromImage(image)
        return image

    def _load_svg(self, data: bytes) -> QImage:
        renderer = QSvgRenderer(QByteArray(data))
        if not renderer.isValid():
            raise ValueError("SVGの読み込みに失敗")

        size = renderer.defaultSize()
        if not size.isValid():
            size = QSize(512, 512)

        image = QImage(size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        renderer.render(painter)
        painter.end()

        return image

