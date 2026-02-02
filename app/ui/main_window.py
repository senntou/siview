from PySide6.QtGui import QFont, QImage
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QThread, Signal

from sftp.client import SFTPClientWrapper
from image.loader import ImageLoader
from ui.file_list_panel import FileListPanel
from ui.image_viewer import ImageViewer


class SFTPConnectWorker(QThread):
    """SFTP接続を行うワーカースレッド"""
    connected = Signal(str)  # 接続完了時に初期パスを送信
    error = Signal(str)      # エラー発生時

    def __init__(self, host: str, parent=None):
        super().__init__(parent)
        self.host = host
        self.client: SFTPClientWrapper | None = None

    def run(self):
        try:
            self.client = SFTPClientWrapper(self.host)
            initial_path = self.client.pwd()
            self.connected.emit(initial_path)
        except Exception as e:
            self.error.emit(str(e))


class SFTPListWorker(QThread):
    """ファイル一覧を取得するワーカースレッド"""
    finished = Signal(str, list)  # (path, entries) entries: list of dict
    error = Signal(str)

    def __init__(self, client: SFTPClientWrapper, path: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.path = path

    def run(self):
        try:
            entries = self.client.ls(self.path)
            entries.sort()

            result = []
            for name in entries:
                full_path = f"{self.path}/{name}"
                is_dir = self.client.is_dir(full_path)
                result.append({"name": name, "is_dir": is_dir})

            self.finished.emit(self.path, result)
        except Exception as e:
            self.error.emit(str(e))


class SFTPFileWorker(QThread):
    """ファイルを取得して画像として読み込むワーカースレッド"""
    finished = Signal(QImage, str)  # (image, filename)
    error = Signal(str)

    def __init__(self, client: SFTPClientWrapper, remote_path: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.remote_path = remote_path
        self._loader = ImageLoader()

    def run(self):
        try:
            data, filename = self.client.get_file(self.remote_path)
            image = self._loader.load(data, filename)
            self.finished.emit(image, filename)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("SIView")
        self.setGeometry(300, 100, 1200, 800)

        # SFTP関連（非同期で初期化）
        self.client: SFTPClientWrapper | None = None
        self.current_path: str | None = None
        self._loading = False

        # UI コンポーネント
        self.file_list_panel = FileListPanel()
        self.image_viewer = ImageViewer()

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.file_list_panel)
        splitter.addWidget(self.image_viewer)
        splitter.setSizes([1, 5])

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        # ワーカー参照を保持（GC防止）
        self._connect_worker: SFTPConnectWorker | None = None
        self._list_worker: SFTPListWorker | None = None
        self._file_worker: SFTPFileWorker | None = None

        # キーシーケンス用（gg等の連続キー入力）
        self._pending_key: str | None = None

        # 初期状態：ローディング表示
        self.file_list_panel.set_message("接続中...")

        # 非同期でSFTP接続を開始
        self._start_connect()

    def _start_connect(self):
        """SFTP接続を非同期で開始"""
        self._connect_worker = SFTPConnectWorker("kronecker", self)
        self._connect_worker.connected.connect(self._on_connected)
        self._connect_worker.error.connect(self._on_connect_error)
        self._connect_worker.start()

    def _on_connected(self, initial_path: str):
        """SFTP接続完了時のコールバック"""
        if self._connect_worker is None:
            raise RuntimeError("Connected but worker is None")
        self.client = self._connect_worker.client
        self.current_path = initial_path
        self._refresh_file_list()

    def _on_connect_error(self, error_msg: str):
        """SFTP接続エラー時のコールバック"""
        self.file_list_panel.set_message(f"接続エラー: {error_msg}")

    def _refresh_file_list(self):
        """現在のディレクトリのファイル一覧を非同期で更新"""
        if self.client is None or self._loading:
            return

        self._loading = True
        self.file_list_panel.set_message("読み込み中...")

        if self.current_path is None:
            raise RuntimeError("Current path is None while refreshing file list")

        self._list_worker = SFTPListWorker(self.client, self.current_path, self)
        self._list_worker.finished.connect(self._on_list_finished)
        self._list_worker.error.connect(self._on_list_error)
        self._list_worker.start()

    def _on_list_finished(self, path: str, entries: list):
        """ファイル一覧取得完了時のコールバック"""
        self._loading = False
        self.file_list_panel.set_entries(entries)
        self.setWindowTitle(f"SIView - {path}")

    def _on_list_error(self, error_msg: str):
        """ファイル一覧取得エラー時のコールバック"""
        self._loading = False
        self.file_list_panel.set_message(f"エラー: {error_msg}")

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

    def _open_file(self):
        """選択中のファイルを開いて画像として表示"""
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

        # 非同期でファイルを取得
        self._file_worker = SFTPFileWorker(self.client, remote_path, self)
        self._file_worker.finished.connect(self._on_file_loaded)
        self._file_worker.error.connect(self._on_file_error)
        self._file_worker.start()

    def _on_file_loaded(self, image: QImage, filename: str):
        """ファイル読み込み完了時のコールバック"""
        self.image_viewer.set_image(image)

    def _on_file_error(self, error_msg: str):
        """ファイル読み込みエラー時のコールバック"""
        self.image_viewer.set_text(f"エラー: {error_msg}")

    def keyPressEvent(self, event):
        """キー入力イベントの処理（Vim風キーバインド）"""
        key = event.key()
        modifiers = event.modifiers()

        # ggシーケンスの処理
        if self._pending_key == "g":
            self._pending_key = None
            if key == Qt.Key.Key_G:
                self.file_list_panel.go_top()
                return
            # gの後に別のキーが来た場合は無視して続行

        # Ctrl修飾キー
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_D:
                self.file_list_panel.move_cursor(15)
                return
            elif key == Qt.Key.Key_U:
                self.file_list_panel.move_cursor(-15)
                return

        # 通常キー
        if key == Qt.Key.Key_Q:
            self.close()
        elif key == Qt.Key.Key_J:
            self.file_list_panel.move_cursor_wrap(1)
        elif key == Qt.Key.Key_K:
            self.file_list_panel.move_cursor_wrap(-1)
        elif key == Qt.Key.Key_H:
            self._go_parent()
        elif key == Qt.Key.Key_L:
            self._enter_directory()
        elif key == Qt.Key.Key_O:
            self._open_file()
        elif key == Qt.Key.Key_G:
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                # Shift+G (大文字G) で一番下
                self.file_list_panel.go_bottom()
            else:
                # 小文字g: ggシーケンスの開始
                self._pending_key = "g"
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """ウィンドウを閉じるときにSFTP接続をクローズ"""
        if self.client is not None:
            self.client.close()
        super().closeEvent(event)
