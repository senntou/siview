from PySide6.QtGui import QFontMetrics, QImage
from PySide6.QtWidgets import QLabel, QSizePolicy, QSplitter, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from ui.thread.workers import HTTPFileWorker, HTTPListWorker, ServerConnectWorker
from ui.host_dialog import HostDialog
from const import FONT_SIZE

from server.manager import ServerManager
from api.client import HTTPClient
from state.manager import StateManager
from ui.file_list_panel import FileListPanel
from ui.image_viewer import ImageViewer
from util.loader import load_stylesheet


class MainWindow(QWidget):
    def __init__(self, host: str, parent=None):
        super().__init__(parent)

        self.host = host
        self.setWindowTitle(f"SIView - {host}")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            #imageLabel {
                background-color: #1e1e1e;
            }
            #textView {
                background-color: #252526;
                color: #dddddd;
                border: none;
            }
        """)

        # 状態管理
        self.state = StateManager(host)

        # サーバー・HTTP関連（非同期で初期化）
        self.manager: ServerManager | None = None
        self.client: HTTPClient | None = None
        self.current_path: str | None = None
        self._home_dir: str | None = None
        self._loading = False

        # 画像パスリスト
        self._image_paths: list[str] = []
        self._current_image_index: int = -1

        # UI コンポーネント
        self._current_display_path = ""  # 省略表示用にフルパスを保持

        # カレントパス毎に、カーソルのインデックスを保存する
        self._path_cursor_map: dict[str, int] = {}

        self.path_label = QLabel()
        self.path_label.setObjectName("pathLabel")
        self.path_label.setStyleSheet(f"""
            #pathLabel {{
                background-color: #cce;
                color: black;
                padding: 4px 8px;
                font-size: {FONT_SIZE};
            }}
        """)
        # 高さを1行分に固定、横は親に合わせる
        self.path_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.path_label.setFixedHeight(28)

        self.file_list_panel = FileListPanel()
        self.image_viewer = ImageViewer()

        # フォーカスモード: "file_list" or "image_viewer"
        self._focus_mode = "file_list"
        self._update_focus_style()

        self._init_keymap()

        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.file_list_panel)
        self.splitter.addWidget(self.image_viewer)

        ratio = 0.3
        size = self.width()
        self.splitter.setSizes([int(size * ratio), int(size * (1 - ratio))])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.path_label)
        layout.addWidget(self.splitter)

        # ワーカー参照を保持（GC防止）
        self._connect_worker: ServerConnectWorker | None = None
        self._list_worker: HTTPListWorker | None = None
        self._file_worker: HTTPFileWorker | None = None

        # キーシーケンス用（gg等の連続キー入力）
        self._pending_key: str | None = None

        # 初期状態：ローディング表示
        self.file_list_panel.set_message("サーバーをセットアップ中...")

        # 非同期でサーバー接続を開始
        self._start_connect()

    def _move_splitter(self, delta: int):
        """スプリッターの位置を調整"""
        sizes = self.splitter.sizes()
        total = sum(sizes)
        ratio = sizes[0] / total
        new_ratio = (ratio + delta * 0.01)
        new_ratio = max(0.1, min(0.9, new_ratio))  # 制限
        self.splitter.setSizes([int(new_ratio * total), int((1 - new_ratio) * total)])

    def _focus_left(self):
        """左のウィジェット(file_list)にフォーカス"""
        if self._focus_mode != "file_list":
            self._focus_mode = "file_list"
            self._update_focus_style()

    def _focus_right(self):
        """右のウィジェット(image_viewer)にフォーカス"""
        if self._focus_mode != "image_viewer":
            self._focus_mode = "image_viewer"
            self._update_focus_style()

    def _update_focus_style(self):
        """フォーカス状態に応じてスタイルを更新"""
        self.file_list_panel.set_focused(self._focus_mode == "file_list")
        self.image_viewer.set_focused(self._focus_mode == "image_viewer")

    def _start_connect(self):
        """サーバーセットアップを非同期で開始"""
        self._connect_worker = ServerConnectWorker(self.host, self)
        self._connect_worker.connected.connect(self._on_connected)
        self._connect_worker.progress.connect(self._on_progress)
        self._connect_worker.error.connect(self._on_connect_error)
        self._connect_worker.start()

    def _on_progress(self, message: str):
        """進捗メッセージを表示"""
        self.file_list_panel.set_message(message)

    def _on_connected(self, home_dir: str):
        """サーバー接続完了時のコールバック"""
        if self._connect_worker is None:
            raise RuntimeError("Connected but worker is None")
        self.manager = self._connect_worker.manager
        self.client = self._connect_worker.client
        self._home_dir = home_dir

        # 接続成功したホスト名を保存
        self.state.set_last_host(self.host)

        # 保存されたパスがあればそれを使用、なければホームディレクトリ
        saved_path = self.state.get_current_dir()
        self.current_path = saved_path if saved_path else home_dir

        self._refresh_file_list()

    def _on_connect_error(self, error_msg: str):
        """サーバー接続エラー時のコールバック"""
        self.file_list_panel.set_message(f"接続エラー: {error_msg}")

    def _show_host_dialog(self):
        """ホスト選択ダイアログを表示"""
        # グローバル状態から履歴を取得
        global_state = StateManager()
        history = global_state.get_host_history()

        dialog = HostDialog(history, self.host, self)
        if dialog.exec() != HostDialog.DialogCode.Accepted:
            return

        new_host = dialog.selected_host()
        if not new_host or new_host == self.host:
            return

        # ホストを変更して再接続
        self._change_host(new_host)

    def _change_host(self, new_host: str):
        """ホストを変更して再接続"""
        # 現在の接続をクリーンアップ
        if self.manager is not None:
            self.manager.cleanup()
            self.manager = None

        self.client = None
        self._home_dir = None
        self.current_path = None

        # 画像リストをクリア
        self._image_paths.clear()
        self._current_image_index = -1
        self.image_viewer.clear_image()
        self.image_viewer.set_pagination(0, 0)

        # 新しいホストに切り替え
        self.host = new_host
        self.state = StateManager(new_host)
        self.setWindowTitle(f"SIView - {new_host}")

        # 再接続
        self.file_list_panel.set_message("サーバーをセットアップ中...")
        self._start_connect()

    def _refresh_file_list(self):
        """現在のディレクトリのファイル一覧を非同期で更新"""
        if self.client is None or self._loading:
            return

        self._loading = True
        self.file_list_panel.set_message("読み込み中...")

        if self.current_path is None:
            raise RuntimeError("Current path is None while refreshing file list")

        self._list_worker = HTTPListWorker(self.client, self.current_path, self)
        self._list_worker.finished.connect(self._on_list_finished)
        self._list_worker.error.connect(self._on_list_error)
        self._list_worker.start()

    def _on_list_finished(self, path: str, entries: list):
        """ファイル一覧取得完了時のコールバック"""
        self._loading = False
        idx = self._path_cursor_map.get(path, 0)
        self.file_list_panel.set_entries(entries, idx)
        self.setWindowTitle(f"SIView - {self.host}:{path}")
        self._set_path_label(path)

        # カレントディレクトリを保存
        self.state.set_current_dir(path)

    def _set_path_label(self, path: str):
        """パスラベルを設定（長すぎる場合は省略）"""
        self._current_display_path = path
        self._update_path_label()

    def _update_path_label(self):
        """パスラベルの表示を更新（ウィンドウ幅に合わせて省略）"""
        if not self._current_display_path:
            return

        font_metrics = QFontMetrics(self.path_label.font())
        available_width = self.path_label.width() - 24  # padding分を引く
        elided = font_metrics.elidedText(
            self._current_display_path,
            Qt.TextElideMode.ElideLeft,  # 左側を省略（末尾のディレクトリ名を優先）
            available_width
        )
        self.path_label.setText(elided)

    def _on_list_error(self, error_msg: str):
        """ファイル一覧取得エラー時のコールバック"""
        self._loading = False
        self.file_list_panel.set_message(f"ファイル一覧取得エラー: {error_msg}")

    def _go_parent(self):
        """親ディレクトリに移動"""
        if self._loading or self.current_path is None or self.current_path == "/":
            return

        # 親ディレクトリを計算
        parent = "/".join(self.current_path.rstrip("/").split("/")[:-1])
        if not parent:
            parent = "/"

        self.current_path = parent
        self._refresh_file_list()

    def _enter_directory(self):
        """選択中のディレクトリに入る"""
        if self._loading or self.current_path is None:
            return

        entry = self.file_list_panel.current_entry()
        if entry is None or not entry["is_dir"]:
            return

        # ディレクトリに移動
        name = entry["name"]
        if self.current_path == "/":
            self.current_path = f"/{name}"
        else:
            self.current_path = f"{self.current_path}/{name}"

        self._refresh_file_list()
    
    def _move_file_cursor(self, delta: int):
        """ファイルリストのカーソルを移動"""
        if self._loading:
            return

        new_row = self.file_list_panel.move_cursor_wrap(delta)
        # カーソル位置を保存
        if self.current_path is not None:
            self._path_cursor_map[self.current_path] = new_row

    def _add_image_to_list(self):
        """選択中のファイルを画像リストに追加"""
        if self._loading or self.client is None or self.current_path is None:
            return

        entry = self.file_list_panel.current_entry()
        if entry is None or entry["is_dir"]:
            return

        # ファイルのフルパスを構築
        name = entry["name"]
        if self.current_path == "/":
            remote_path = f"/{name}"
        else:
            remote_path = f"{self.current_path}/{name}"

        # 既にリストにある場合はその画像を表示
        if remote_path in self._image_paths:
            self._current_image_index = self._image_paths.index(remote_path)
            self._show_current_image()
            return

        # リストに追加
        self._image_paths.append(remote_path)
        self._current_image_index = len(self._image_paths) - 1
        self._show_current_image()

    def _remove_current_image(self):
        """現在表示中の画像をリストから削除"""
        if not self._image_paths or self._current_image_index < 0:
            return

        self._image_paths.pop(self._current_image_index)

        if not self._image_paths:
            # リストが空になった
            self._current_image_index = -1
            self.image_viewer.clear_image()
            self.image_viewer.set_pagination(0, 0)
            return

        # インデックスを調整
        if self._current_image_index >= len(self._image_paths):
            self._current_image_index = len(self._image_paths) - 1

        self._show_current_image()

    def _show_current_image(self):
        """現在のインデックスの画像を表示"""
        if not self._image_paths or self._current_image_index < 0:
            return

        remote_path = self._image_paths[self._current_image_index]
        filename = remote_path.split("/")[-1]
        self._load_image(remote_path)
        self.image_viewer.set_filename(filename)
        self.image_viewer.set_pagination(self._current_image_index, len(self._image_paths))

    def _next_image(self):
        """次の画像を表示"""
        if not self._image_paths:
            return
        self._current_image_index = (self._current_image_index + 1) % len(self._image_paths)
        self._show_current_image()

    def _prev_image(self):
        """前の画像を表示"""
        if not self._image_paths:
            return
        self._current_image_index = (self._current_image_index - 1) % len(self._image_paths)
        self._show_current_image()

    def _load_image(self, remote_path: str):
        """指定パスの画像を非同期で読み込み"""
        if self.client is None:
            return

        self._file_worker = HTTPFileWorker(self.client, remote_path, self)
        self._file_worker.finished.connect(self._on_file_loaded)
        self._file_worker.error.connect(self._on_file_error)
        self._file_worker.start()

    def _on_file_loaded(self, image: QImage, filename: str):
        """ファイル読み込み完了時のコールバック"""
        self.image_viewer.set_image(image)

    def _on_file_error(self, error_msg: str):
        """ファイル読み込みエラー時のコールバック"""
        self.image_viewer.set_text(f"画像読み込みエラー: {error_msg}")

    def _init_keymap(self):
        self._pending_key = None

        # グローバルキーマップ（全モード共通）
        self._global_keymap = {
            (Qt.Key.Key_Q,): self.close,
            ("Ctrl", Qt.Key.Key_H): lambda: self._move_splitter(-3),
            ("Ctrl", Qt.Key.Key_L): lambda: self._move_splitter(3),
            ("Shift", Qt.Key.Key_H): self._focus_left,
            ("Shift", Qt.Key.Key_L): self._focus_right,
            ("Shift", Qt.Key.Key_R): self._show_host_dialog,
        }

        # モード別キーマップ
        self._mode_keymaps = {
            "file_list": {
                (Qt.Key.Key_J,): lambda: self._move_file_cursor(1),
                (Qt.Key.Key_K,): lambda: self._move_file_cursor(-1),
                (Qt.Key.Key_H,): self._go_parent,
                (Qt.Key.Key_L,): self._enter_directory,
                (Qt.Key.Key_O,): self._add_image_to_list,
                ("Ctrl", Qt.Key.Key_D): lambda: self.file_list_panel.move_cursor(15),
                ("Ctrl", Qt.Key.Key_U): lambda: self.file_list_panel.move_cursor(-15),
                ("Shift", Qt.Key.Key_G): self.file_list_panel.go_bottom,
            },
            "image_viewer": {
                (Qt.Key.Key_J,): self._next_image,
                (Qt.Key.Key_K,): self._prev_image,
                (Qt.Key.Key_D,): self._remove_current_image,
            },
        }

        # モード別シーケンス
        self._mode_sequences = {
            "file_list": {
                (Qt.Key.Key_G, Qt.Key.Key_G): self.file_list_panel.go_top,
            },
            "image_viewer": {
            },
        }


    def keyPressEvent(self, event):
        """Vim風キーバインド（モード対応）"""

        # ---------- キー正規化 ----------
        parts = []
        mods = event.modifiers()

        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")

        parts.append(event.key())
        key_id = tuple(parts)

        # ---------- シーケンス処理 ----------
        if self._pending_key is not None:
            seq = (self._pending_key, event.key())
            self._pending_key = None

            sequences = self._mode_sequences.get(self._focus_mode, {})
            action = sequences.get(seq)
            if action:
                action()
                return

        # ---------- グローバルキー ----------
        action = self._global_keymap.get(key_id)
        if action:
            action()
            return

        # ---------- モード別キー ----------
        mode_keymap = self._mode_keymaps.get(self._focus_mode, {})
        action = mode_keymap.get(key_id)
        if action:
            action()
            return

        # ---------- シーケンス開始（モード別） ----------
        sequences = self._mode_sequences.get(self._focus_mode, {})
        for seq in sequences:
            if seq[0] == event.key():
                self._pending_key = event.key()
                return

        super().keyPressEvent(event)

    def resizeEvent(self, event):
        """ウィンドウリサイズ時にパスラベルを更新"""
        super().resizeEvent(event)
        self._update_path_label()

    def closeEvent(self, event):
        """ウィンドウを閉じるときにサーバーをクリーンアップ"""
        if self.manager is not None:
            self.manager.cleanup()
        super().closeEvent(event)
