from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu, QTextEdit, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QFont, QFontMetrics, QGuiApplication, QPixmap, QImage
from PySide6.QtCore import Qt, QTimer

from const import BG_DEFAULT, BG_FOCUSED, BORDER_FOCUSED, BORDER_DEFAULT, FONT_SIZE, TEXT_DEFAULT


class ImageViewer(QFrame):
    """画像とテキストを表示するビューア"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("imageViewer")
        self._pixmap: QPixmap | None = None
        self._is_focused: bool = False

        # 枠線設定
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(4)
        self.set_focused(False)

        # ページネーション表示
        self.pagination_label = QLabel()
        self.pagination_label.setObjectName("paginationLabel")
        self.pagination_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pagination_label.setStyleSheet(f"""
            #paginationLabel {{
                color: {TEXT_DEFAULT};
                padding: 4px;
            }}
        """)
        self._set_label_font(self.pagination_label, FONT_SIZE)

        # 画像表示
        self.image_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.image_label.setObjectName("imageLabel")
        self.image_label.setMinimumSize(1, 1)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        # ファイル名表示
        self.filename_label = QLabel()
        self.filename_label.setObjectName("filenameLabel")
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setStyleSheet(f"""
            #filenameLabel {{
                color: {TEXT_DEFAULT};
                padding: 4px;
            }}
        """)
        self._set_label_font(self.filename_label, FONT_SIZE)

        # テキスト表示
        self.text_view = QTextEdit(readOnly=True)
        self.text_view.setObjectName("textView")

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)

        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self.pagination_label)
        layout.addWidget(self.image_label, 8)
        layout.addWidget(self.filename_label)
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
        self._is_focused = focused
        bg = BG_FOCUSED if focused else BG_DEFAULT
        border = BORDER_FOCUSED if focused else BORDER_DEFAULT
        self.setStyleSheet(f"""
            #imageViewer {{ border: 4px solid {border}; background-color: {bg}; }}
            #imageLabel {{ background-color: {bg}; }}
        """)

    def _open_context_menu(self, pos):
        if self._pixmap is None:
            return

        menu = QMenu(self)
        menu.addAction("コピー", self._copy_image)
        menu.addAction("保存", self._save_image)
        menu.exec(self.mapToGlobal(pos))

    def _copy_image(self):
        if self._pixmap is None:
            return
        QGuiApplication.clipboard().setPixmap(self._pixmap)
        self._show_copy_feedback()

    def _show_copy_feedback(self):
        """コピー完了のフィードバックを表示"""
        # 枠をフラッシュ
        self._flash_border()
        # テキストを一時的に表示
        original_text = self.text_view.toPlainText()
        self.text_view.setPlainText("クリップボードにコピーしました")
        QTimer.singleShot(1500, lambda: self.text_view.setPlainText(original_text))

    def _flash_border(self):
        """枠を一時的にハイライト"""
        flash_color = "#FFFF00"  # 黄色でフラッシュ
        bg = BG_FOCUSED if self._is_focused else BG_DEFAULT
        self.setStyleSheet(f"""
            #imageViewer {{ border: 4px solid {flash_color}; background-color: {bg}; }}
            #imageLabel {{ background-color: {bg}; }}
        """)
        QTimer.singleShot(300, lambda: self.set_focused(self._is_focused))

    def _save_image(self):
        if self._pixmap is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "画像を保存",
            "",
            "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        if path:
            self._pixmap.save(path)


    def clear_image(self):
        """画像をクリア"""
        self._pixmap = None
        self.image_label.clear()
        self.filename_label.setText("")

    def set_filename(self, filename: str):
        """ファイル名を設定"""
        self.filename_label.setText(filename)

    def set_text(self, text: str):
        """テキストを設定"""
        self.text_view.setPlainText(text)

    def clear_text(self):
        """テキストをクリア"""
        self.text_view.clear()

    def set_pagination(self, current: int, total: int):
        """ページネーション表示を更新"""
        if total == 0:
            self.pagination_label.setText("")
        else:
            self.pagination_label.setText(f"{current + 1} / {total}")

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

    def _set_label_font(self, label: QLabel, size: int):
        """ラベルにフォントサイズと高さを設定（Windows対応）"""
        font = label.font()
        font.setPixelSize(size)
        label.setFont(font)
        # フォントサイズに合わせて高さを調整（パディング含む）
        metrics = QFontMetrics(font)
        label.setFixedHeight(metrics.height() + 10)

    def set_font_size(self, size: int):
        """全ラベルのフォントサイズを設定"""
        self._set_label_font(self.pagination_label, size)
        self._set_label_font(self.filename_label, size)
