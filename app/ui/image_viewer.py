from PySide6.QtWidgets import QFrame, QLabel, QTextEdit, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


class ImageViewer(QFrame):
    """画像とテキストを表示するビューア"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("imageViewer")
        self._pixmap: QPixmap | None = None

        # 枠線設定
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(4)
        self._update_border(False)

        # 画像表示
        self.image_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.image_label.setObjectName("imageLabel")
        self.image_label.setMinimumSize(1, 1)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        # テキスト表示
        self.text_view = QTextEdit(readOnly=True)
        self.text_view.setObjectName("textView")

        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.image_label, 4)
        layout.addWidget(self.text_view, 1)

    def set_image(self, image: str | QImage | QPixmap):
        """画像を設定"""
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

    def set_focused(self, focused: bool):
        """フォーカス状態を設定"""
        self._update_border(focused)

    def _update_border(self, focused: bool):
        """枠線のスタイルを更新"""
        if focused:
            self.setStyleSheet("#imageViewer { border: 4px solid #4ec9b0; }")
        else:
            self.setStyleSheet("#imageViewer { border: 4px solid transparent; }")

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
