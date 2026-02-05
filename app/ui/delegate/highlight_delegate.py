from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QTextDocument, QAbstractTextDocumentLayout
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle


class HighlightDelegate(QStyledItemDelegate):
    """フィルタパターンにマッチする文字をハイライトするデリゲート"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._highlight_pattern: str = ""
        self._highlight_color = "#FFFF00"

    def set_highlight_pattern(self, pattern: str):
        """ハイライトするパターンを設定"""
        self._highlight_pattern = pattern.lower()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        # 選択状態の背景を描画
        self.initStyleOption(option, index)
        style = option.widget.style() if option.widget else None

        if style:
            style.drawPrimitive(QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter, option.widget)

        # アイコンを描画
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon:
            icon_rect = QRect(
                option.rect.left() + 4,
                option.rect.top() + (option.rect.height() - 20) // 2,
                20, 20
            )
            icon.paint(painter, icon_rect)

        # テキスト描画領域
        text_rect = QRect(
            option.rect.left() + 28,
            option.rect.top(),
            option.rect.width() - 32,
            option.rect.height()
        )

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            return

        # ハイライトがない場合は通常描画
        if not self._highlight_pattern or self._highlight_pattern not in text.lower():
            painter.save()
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(option.palette.highlightedText().color())
            else:
                painter.setPen(option.palette.text().color())
            painter.setFont(option.font)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            painter.restore()
            return

        # ハイライト付きで描画（HTMLを使用）
        html = self._build_highlighted_html(text, option)
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(html)

        painter.save()
        painter.translate(text_rect.topLeft())
        painter.setClipRect(QRect(0, 0, text_rect.width(), text_rect.height()))

        # 垂直中央揃え
        y_offset = (text_rect.height() - doc.size().height()) / 2
        painter.translate(0, y_offset)

        ctx = QAbstractTextDocumentLayout.PaintContext()
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def _build_highlighted_html(self, text: str, option: QStyleOptionViewItem) -> str:
        """ハイライト付きHTMLを構築"""
        if option.state & QStyle.StateFlag.State_Selected:
            text_color = option.palette.highlightedText().color().name()
        else:
            text_color = option.palette.text().color().name()

        pattern = self._highlight_pattern
        text_lower = text.lower()
        result = []
        i = 0

        while i < len(text):
            pos = text_lower.find(pattern, i)
            if pos == -1:
                result.append(self._escape_html(text[i:]))
                break
            if pos > i:
                result.append(self._escape_html(text[i:pos]))
            matched = text[pos:pos + len(pattern)]
            result.append(f'<span style="background-color:{self._highlight_color}; color:black;">{self._escape_html(matched)}</span>')
            i = pos + len(pattern)

        return f'<span style="color:{text_color};">{"".join(result)}</span>'

    @staticmethod
    def _escape_html(text: str) -> str:
        """HTML特殊文字をエスケープ"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
