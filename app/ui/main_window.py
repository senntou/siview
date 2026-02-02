from PySide6.QtWidgets import (
    QWidget, QLabel, QTextEdit, QHBoxLayout
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("SIView")
        self.setGeometry(300, 100, 1200, 800)

        # 左：テキスト表示
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)

        # 右：画像表示
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 200)

        self._pixmap = None  # 元画像保持用

        # レイアウト
        layout = QHBoxLayout()
        layout.addWidget(self.text_view, 1)
        layout.addWidget(self.image_label, 1)
        self.setLayout(layout)

    # ---------- 左側 ----------
    def set_file_list(self, file_list):
        """
        file_list: list[str]
        """
        self.text_view.clear()
        self.text_view.setPlainText("\n".join(file_list))

    # ---------- 右側 ----------
    def set_image(self, image):
        """
        image: str (path) | QImage | QPixmap
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_image()

    def keyPressEvent(self, event):
        """キー入力イベントの処理"""
        if event.key() == Qt.Key_Q:
            self.close()
        else:
            super().keyPressEvent(event)

    def _update_image(self):
        if self._pixmap is None:
            return

        scaled = self._pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

