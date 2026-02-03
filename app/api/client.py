"""
SFTPClientWrapper互換のHTTPクライアント

ローカルポート9000経由でリモートのsiview-serverと通信
"""

import posixpath
import urllib.parse
import urllib.request
import json
from typing import List, Tuple


class HTTPClient:
    """
    HTTPベースのファイルアクセスクライアント
    SFTPClientWrapperと互換のインターフェースを提供
    """

    def __init__(self, base_url: str = "http://127.0.0.1:9000", home_dir: str = "/"):
        self.base_url = base_url.rstrip("/")
        self._cwd = home_dir
        self._home_dir = home_dir

    def ls(self, path: str = ".") -> List[dict]:
        """
        指定ディレクトリのファイル一覧を返す

        Returns:
            list of dict: [{"name": str, "is_dir": bool, "size": int}, ...]
        """
        # 相対パスを絶対パスに変換
        if not path.startswith("/"):
            if path == ".":
                abs_path = self._cwd
            else:
                abs_path = f"{self._cwd}/{path}"
        else:
            abs_path = path

        # パスを正規化（リモートは常にPOSIXパス）
        abs_path = posixpath.normpath(abs_path)

        # ホームディレクトリからの相対パスに変換
        rel_path = self._to_relative_path(abs_path)

        url = f"{self.base_url}/api/list?path={urllib.parse.quote(rel_path)}"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data

    def get_file(self, remote_path: str) -> Tuple[bytes, str]:
        """
        ファイルをメモリに取得

        Returns:
            data (bytes): ファイルの中身
            filename (str): ファイル名のみ
        """
        # ホームディレクトリからの相対パスに変換
        rel_path = self._to_relative_path(remote_path)

        url = f"{self.base_url}/file/{urllib.parse.quote(rel_path)}"
        with urllib.request.urlopen(url) as response:
            data = response.read()

        filename = posixpath.basename(remote_path)
        return data, filename

    def pwd(self) -> str:
        """現在のワーキングディレクトリを返す"""
        return self._cwd

    def chdir(self, path: str):
        """ワーキングディレクトリを変更"""
        if path.startswith("/"):
            self._cwd = path
        else:
            self._cwd = posixpath.normpath(f"{self._cwd}/{path}")

    def is_dir(self, path: str) -> bool:
        """パスがディレクトリかどうかを判定"""
        # 親ディレクトリの一覧を取得して判定
        parent = posixpath.dirname(path)
        name = posixpath.basename(path)

        try:
            entries = self.ls(parent)
            for entry in entries:
                if entry["name"] == name:
                    return entry["is_dir"]
        except Exception:
            pass

        return False

    def close(self):
        """接続を閉じる（HTTPなので特に何もしない）"""
        pass

    def _to_relative_path(self, abs_path: str) -> str:
        """
        絶対パスをホームディレクトリからの相対パスに変換

        例: /home/user/foo → foo (home_dir が /home/user の場合)
        """
        # パスを正規化（リモートは常にPOSIXパス）
        abs_path = posixpath.normpath(abs_path)

        # ホームディレクトリからの相対パス
        if abs_path.startswith(self._home_dir):
            rel = abs_path[len(self._home_dir):]
            if rel.startswith("/"):
                rel = rel[1:]
            return rel if rel else "."
        else:
            # ホームディレクトリ外のパスはそのまま返す（エラーになる可能性あり）
            return abs_path

    # with 構文対応
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
