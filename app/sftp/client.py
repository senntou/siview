import os
import paramiko
from io import BytesIO
from typing import List, Tuple


class SFTPClientWrapper:
    """
    ~/.ssh/config を利用して host 名だけで接続できる SFTP クライアント
    """

    def __init__(self, host: str, ssh_config_path: str = "~/.ssh/config"):
        self.host = host
        self.ssh_config_path = os.path.expanduser(ssh_config_path)

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        config = self._load_ssh_config()
        self._connect(config)

        self.sftp = self.ssh.open_sftp()

    def _load_ssh_config(self) -> dict:
        config = paramiko.SSHConfig()
        with open(self.ssh_config_path) as f:
            config.parse(f)

        host_config = config.lookup(self.host)
        if not host_config:
            raise ValueError(f"Host '{self.host}' not found in ssh config")

        return host_config

    def _connect(self, config: dict):
        hostname = config.get("hostname", self.host)
        username = config.get("user", None)
        port = int(config.get("port", 22))
        identityfile = config.get("identityfile", [None])[0]

        self.ssh.connect(
            hostname=hostname,
            port=port,
            username=username,
            key_filename=identityfile,
        )

    # ----------------------------
    # public API
    # ----------------------------

    def ls(self, path: str = ".") -> List[str]:
        """
        指定ディレクトリのファイル一覧を返す
        相対 / 絶対パス両対応
        """
        return self.sftp.listdir(path)

    def get_file(self, remote_path: str) -> Tuple[bytes, str]:
        """
        ファイルをメモリに取得

        Returns:
            data (bytes): ファイルの中身
            filename (str): ファイル名のみ
        """
        bio = BytesIO()
        self.sftp.getfo(remote_path, bio)
        bio.seek(0)

        filename = os.path.basename(remote_path)
        return bio.read(), filename

    def close(self):
        self.sftp.close()
        self.ssh.close()

    # with 構文対応
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

