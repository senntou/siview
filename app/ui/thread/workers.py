from PySide6.QtGui import QImage
from PySide6.QtCore import QThread, Signal

from server.manager import ServerManager
from api.client import HTTPClient
from image.loader import ImageLoader

class ServerConnectWorker(QThread):
    """サーバーセットアップを行うワーカースレッド"""
    connected = Signal(str)  # 接続完了時に初期パスを送信
    progress = Signal(str)   # 進捗メッセージ
    error = Signal(str)      # エラー発生時

    def __init__(self, host: str, parent=None):
        super().__init__(parent)
        self.host = host
        self.manager: ServerManager | None = None
        self.client: HTTPClient | None = None
        self._home_dir: str | None = None

    def run(self):
        try:
            self.manager = ServerManager(self.host)
            self._home_dir = self.manager.setup(
                progress_callback=lambda msg: self.progress.emit(msg)
            )
            self.client = HTTPClient(home_dir=self._home_dir)
            self.connected.emit(self._home_dir)
        except Exception as e:
            self.error.emit(str(e))


class HTTPListWorker(QThread):
    """ファイル一覧を取得するワーカースレッド"""
    finished = Signal(str, list)  # (path, entries) entries: list of dict
    error = Signal(str)

    def __init__(self, client: HTTPClient, path: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.path = path

    def run(self):
        try:
            entries = self.client.ls(self.path)

            # 名前でソート
            entries.sort(key=lambda e: e["name"])

            self.finished.emit(self.path, entries)
        except Exception as e:
            self.error.emit(str(e))


class ZoxideAddWorker(QThread):
    """非同期でリモートのzoxide addを実行するワーカー"""

    def __init__(self, manager, path: str, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.path = path

    def run(self):
        try:
            self.manager.zoxide_add(self.path)
        except Exception:
            pass


class HTTPFileWorker(QThread):
    """ファイルを取得して画像として読み込むワーカースレッド"""
    finished = Signal(QImage, str)  # (image, filename)
    error = Signal(str)

    def __init__(self, client: HTTPClient, remote_path: str, parent=None):
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
