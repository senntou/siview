from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu, QTextEdit, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QFont, QFontMetrics, QGuiApplication, QPainter, QPixmap, QImage
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer

from const import BG_DEFAULT, BG_FOCUSED, BORDER_FOCUSED, BORDER_DEFAULT, FONT_SIZE, TEXT_DEFAULT


class ImageViewer(QFrame):
    """画像とテキストを表示するビューア"""

    _ZOOM_STEP = 1.25
    _ZOOM_MIN = 0.1
    _ZOOM_MAX = 10.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("imageViewer")
        self._pixmap: QPixmap | None = None
        self._is_focused: bool = False
        self._zoom_factor: float = 1.0
        self._pan_offset = QPointF(0, 0)
        self._drag_start: QPointF | None = None
        self._drag_offset_start: QPointF | None = None

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
        self.image_label.setMouseTracking(True)
        self.image_label.installEventFilter(self)

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
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
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
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
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

    def eventFilter(self, obj, event):
        """image_label 上のマウス操作を処理する"""
        if obj is not self.image_label:
            return super().eventFilter(obj, event)

        t = event.type()

        # ホイールでズーム
        if t == QEvent.Type.Wheel:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            return True

        # 左ボタン押下でドラッグ開始
        if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position()
            self._drag_offset_start = QPointF(self._pan_offset)
            self.image_label.setCursor(Qt.CursorShape.ClosedHandCursor)
            return True

        # ドラッグ中
        if t == QEvent.Type.MouseMove and self._drag_start is not None:
            delta = event.position() - self._drag_start
            self._pan_offset = self._drag_offset_start + delta
            self._update_image()
            return True

        # ドラッグ終了
        if t == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
            return True

        return super().eventFilter(obj, event)

    def zoom_in(self):
        """ズームイン"""
        self._zoom_factor = min(self._zoom_factor * self._ZOOM_STEP, self._ZOOM_MAX)
        self._update_image()

    def zoom_out(self):
        """ズームアウト"""
        self._zoom_factor = max(self._zoom_factor / self._ZOOM_STEP, self._ZOOM_MIN)
        self._update_image()

    def _clamp_pan_offset(self, image_w: float, image_h: float, label_w: float, label_h: float):
        """パンオフセットを画像がはみ出しすぎないように制限する"""
        max_dx = max(0, (image_w - label_w) / 2)
        max_dy = max(0, (image_h - label_h) / 2)
        self._pan_offset = QPointF(
            max(-max_dx, min(max_dx, self._pan_offset.x())),
            max(-max_dy, min(max_dy, self._pan_offset.y())),
        )

    def _update_image(self):
        """画像をラベルサイズとズーム倍率に合わせて描画する"""
        if self._pixmap is None:
            return

        label_size = self.image_label.size()
        label_w, label_h = label_size.width(), label_size.height()

        # フィットサイズとズーム後の論理サイズを算出
        fitted = self._pixmap.size().scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        zoomed_w = fitted.width() * self._zoom_factor
        zoomed_h = fitted.height() * self._zoom_factor

        # パンオフセットをクランプ
        self._clamp_pan_offset(zoomed_w, zoomed_h, label_w, label_h)

        # 元画像→ズーム後のスケール比
        scale = zoomed_w / self._pixmap.width()

        # ズーム後画像の左上座標（ラベル座標系）
        img_x = (label_w - zoomed_w) / 2 + self._pan_offset.x()
        img_y = (label_h - zoomed_h) / 2 + self._pan_offset.y()

        # 座標変換で元画像を直接描画（キャンバス外は自動クリップ）
        canvas = QPixmap(label_size)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(img_x, img_y)
        painter.scale(scale, scale)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.end()

        self.image_label.setPixmap(canvas)

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
