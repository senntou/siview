from PySide6.QtWidgets import QFrame, QListView, QVBoxLayout
from PySide6.QtCore import Qt

from const import (
    BG_DEFAULT, BG_FOCUSED, TEXT_DEFAULT, TEXT_SELECTED,
    BORDER_FOCUSED, BORDER_DEFAULT, ITEM_SELECTED_BG
)
from ui.model.file_list_model import FileListModel


class FileListPanel(QFrame):
    """ファイル一覧を表示するパネル"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("fileListPanel")

        # 枠線設定
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(4)

        # リストビュー
        self._list_view = QListView()
        self._list_view.setObjectName("fileListView")
        self._list_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._model = FileListModel()
        self._list_view.setModel(self._model)
        self._list_view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)

        # スクロールバーを非表示
        self._list_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list_view)

        self._entries: list[dict] = []  # ファイル情報を保持（name, is_dir）

        self._update_style(False)

    def set_focused(self, focused: bool):
        """フォーカス状態を設定"""
        self._update_style(focused)

    def _update_style(self, focused: bool):
        """スタイルを更新"""
        bg = BG_FOCUSED if focused else BG_DEFAULT
        border = BORDER_FOCUSED if focused else BORDER_DEFAULT

        self.setStyleSheet(f"#fileListPanel {{ border: 4px solid {border}; background-color: {bg}; }}")
        self._list_view.setStyleSheet(f"""
            #fileListView {{
                background-color: {bg};
                color: {TEXT_DEFAULT};
                border: none;
                font-size: 18px;
            }}
            #fileListView::item {{
                padding: 6px;
            }}
            #fileListView::item:selected {{
                background-color: {ITEM_SELECTED_BG};
                color: {TEXT_SELECTED};
            }}
        """)

    def set_entries(self, entries: list[dict]):
        """ファイルエントリを設定して表示を更新"""
        self._entries = entries

        # 表示用の文字列リストを作成
        display_list = []
        for entry in entries:
            name = entry["name"]
            is_dir = entry["is_dir"]
            display_name = f"{name}/" if is_dir else name
            display_list.append(display_name)

        self._model.set_entries(entries)

        # 最初のアイテムを選択
        if len(display_list) > 0:
            self._list_view.setCurrentIndex(self._model.index(0, 0))

    def set_message(self, message: str):
        """単一メッセージを表示（ローディング、エラー等）"""
        self._entries = []
        self._model.set_entries([{"name": message, "is_dir": False}])

    def current_row(self) -> int:
        """現在選択中の行番号を取得"""
        index = self._list_view.currentIndex()
        return index.row() if index.isValid() else -1

    def set_current_row(self, row: int):
        """指定した行を選択"""
        row = min(max(row, 0), self._model.rowCount() - 1)
        self._list_view.setCurrentIndex(self._model.index(row, 0))

    def move_cursor(self, delta: int):
        """カーソルを上下に移動"""
        current = self.current_row()
        self.set_current_row(current + delta)

    def move_cursor_wrap(self, delta: int):
        """カーソルを上下に移動（端で折り返す）"""
        count = self._model.rowCount()
        if count == 0:
            return
        current = self.current_row()
        new_row = (current + delta) % count
        self.set_current_row(new_row)

    def go_top(self):
        """一番上に移動"""
        self.set_current_row(0)

    def go_bottom(self):
        """一番下に移動"""
        count = self._model.rowCount()
        if count > 0:
            self.set_current_row(count - 1)

    def current_entry(self) -> dict | None:
        """現在選択中のエントリを取得"""
        row = self.current_row()
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def entry_count(self) -> int:
        """エントリ数を取得"""
        return len(self._entries)
