from PySide6.QtWidgets import QWidget, QLabel, QTextEdit, QVBoxLayout
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


class ImageViewer(QWidget):
    """画像とテキストを表示するビューア"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("imageViewer")
        self._pixmap: QPixmap | None = None

        # 画像表示
        self.image_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.image_label.setObjectName("imageLabel")

        # テキスト表示
        self.text_view = QTextEdit(readOnly=True)
        self.text_view.setObjectName("textView")

        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label, 4)
        layout.addWidget(self.text_view, 1)

    def set_image(self, image: str | QImage | QPixmap):
        """
        画像を設定

        Args:
            image: ファイルパス、QImage、またはQPixmap
        """
        if isinstance(image, str):
            pixmap = QPixmap(image)
        elif isinstance(image, QImage):
            pixmap = QPixmap.fromImage(image)
        elif isinstance(image, QPixmap):
            pixmap = image
        else:
            raise TypeError("Unsupported image type")

        self._pixmap = pixmap
        self._update_image()

    def clear_image(self):
        """画像をクリア"""
        self._pixmap = None
        self.image_label.clear()

    def set_text(self, text: str):
        """テキストを設定"""
        self.text_view.setPlainText(text)

    def clear_text(self):
        """テキストをクリア"""
        self.text_view.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_image()

    def _update_image(self):
        """画像をラベルサイズに合わせてスケーリング"""
        if self._pixmap is None:
            return

        scaled = self._pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
