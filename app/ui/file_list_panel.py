from PySide6.QtWidgets import QListView
from PySide6.QtCore import Qt

from ui.model.file_list_model import FileListModel


class FileListPanel(QListView):
    """ファイル一覧を表示するパネル"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("fileListPanel")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # キーイベントを親で処理

        self._model = FileListModel()
        self.setModel(self._model)
        self.setEditTriggers(QListView.EditTrigger.NoEditTriggers)

        # スクロールバーを非表示
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._entries: list[dict] = []  # ファイル情報を保持（name, is_dir）
        self._update_border(False)

    def set_focused(self, focused: bool):
        """フォーカス状態を設定"""
        self._update_border(focused)

    def _update_border(self, focused: bool):
        """枠線のスタイルを更新"""
        border = "4px solid #4ec9b0" if focused else "4px solid transparent"
        self.setStyleSheet(f"""
            #fileListPanel {{
                background-color: #1e1e1e;
                color: #dddddd;
                border: {border};
                font-size: 18px;
            }}
            #fileListPanel::item {{
                padding: 6px;
            }}
            #fileListPanel::item:selected {{
                background-color: #007acc;
                color: white;
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
            self.setCurrentIndex(self._model.index(0, 0))

    def set_message(self, message: str):
        """単一メッセージを表示（ローディング、エラー等）"""
        self._entries = []
        self._model.set_entries([{"name": message, "is_dir": False}])

    def current_row(self) -> int:
        """現在選択中の行番号を取得"""
        index = self.currentIndex()
        return index.row() if index.isValid() else -1

    def set_current_row(self, row: int):
        """指定した行を選択"""
        row = min(max(row, 0), self._model.rowCount() - 1)
        self.setCurrentIndex(self._model.index(row, 0))

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
