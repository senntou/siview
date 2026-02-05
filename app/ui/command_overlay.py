from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import Qt, Signal, QEvent

from const import BG_DEFAULT, BORDER_FOCUSED, TEXT_DEFAULT


class CommandOverlay(QWidget):
    """vim/zathura風のコマンド入力オーバーレイ"""

    command_accepted = Signal(str)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("commandOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        self.setStyleSheet(f"""
            #commandOverlay {{
                background-color: rgba(30, 30, 30, 220);
                border: 2px solid {BORDER_FOCUSED};
                border-radius: 4px;
            }}
        """)

        # レイアウト
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # ":" プレフィックスラベル
        self._prefix = QLabel(":")
        self._prefix.setStyleSheet(f"color: {BORDER_FOCUSED}; font-size: 16px; font-weight: bold;")
        layout.addWidget(self._prefix)

        # コマンド入力欄
        self._input = QLineEdit()
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {TEXT_DEFAULT};
                border: none;
                font-size: 16px;
            }}
        """)
        self._input.returnPressed.connect(self._on_accept)
        self._input.installEventFilter(self)  # フォーカスアウト監視
        layout.addWidget(self._input)

        self.setFixedHeight(36)

    def activate(self, initial_text: str = ""):
        """オーバーレイを表示してフォーカスを設定"""
        self._input.setText(initial_text)
        self._reposition()
        self.show()
        self.raise_()
        self._input.setFocus()
        self._input.setCursorPosition(len(initial_text))

    def _on_accept(self):
        """Enter押下時: コマンドを発行して閉じる"""
        text = self._input.text().strip()
        self.hide()
        if text:
            self.command_accepted.emit(text)

    def keyPressEvent(self, event):
        """EscapeまたはCtrl+Cで入力を破棄して閉じる"""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.parent().setFocus()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """入力欄からフォーカスが外れたら自動で閉じる"""
        if obj is self._input and event.type() == QEvent.Type.FocusOut:
            self.hide()
            self.parent().setFocus()
        return super().eventFilter(obj, event)

    def _reposition(self):
        """親ウィジェットの中央に配置"""
        parent = self.parent()
        if parent is None:
            return
        w = int(parent.width() * 0.5)
        self.setFixedWidth(w)
        x = (parent.width() - w) // 2
        y = (parent.height() - self.height()) // 2
        self.move(x, y)
