"""
ホスト選択ダイアログ
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QLineEdit
)
from PySide6.QtCore import Qt


class HostDialog(QDialog):
    """ホスト名を選択・入力するダイアログ"""

    def __init__(self, history: list[str], current_host: str | None = None, parent=None):
        """
        Args:
            history: 過去に使用したホスト名のリスト
            current_host: 現在のホスト名（デフォルト選択用）
        """
        super().__init__(parent)
        self.setWindowTitle("ホスト選択")
        self.setModal(True)
        self.setMinimumWidth(300)

        self._selected_host: str | None = None

        layout = QVBoxLayout(self)

        # ラベル
        label = QLabel("SSHホスト名を入力または選択:")
        layout.addWidget(label)

        # コンボボックス（編集可能）
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        # 履歴を追加
        for host in history:
            self.combo.addItem(host)

        # 現在のホストまたは最新の履歴をデフォルト選択
        if current_host:
            idx = self.combo.findText(current_host)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
            else:
                self.combo.setEditText(current_host)
        elif history:
            self.combo.setCurrentIndex(0)

        # Enterキーで接続
        self.combo.lineEdit().returnPressed.connect(self._on_connect)

        layout.addWidget(self.combo)

        # ボタン
        button_layout = QHBoxLayout()

        self.connect_btn = QPushButton("接続")
        self.connect_btn.setDefault(True)
        self.connect_btn.clicked.connect(self._on_connect)

        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _on_connect(self):
        """接続ボタン押下時"""
        host = self.combo.currentText().strip()
        if host:
            self._selected_host = host
            self.accept()

    def selected_host(self) -> str | None:
        """選択されたホスト名を取得"""
        return self._selected_host
