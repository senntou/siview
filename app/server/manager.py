"""
サーバーのライフサイクル管理

- SCPでリモート転送
- SSHでサーバー起動
- SSHポートフォワーディング（paramiko direct-tcpip）
- 終了時クリーンアップ
"""

import os
import select
import threading
import socketserver
from pathlib import Path
from typing import Callable

import paramiko


class ServerManager:
    """
    リモートサーバーのデプロイ・起動・トンネル管理
    """

    LOCAL_BINARY = "siview-server-linux-amd64"
    REMOTE_DIR = ".siview/bin"
    REMOTE_BINARY = "siview-server"
    REMOTE_PORT = 9000
    LOCAL_PORT = 9000

    def __init__(self, host: str, ssh_config_path: str = "~/.ssh/config"):
        self.host = host
        self.ssh_config_path = os.path.expanduser(ssh_config_path)

        self.ssh: paramiko.SSHClient | None = None
        self.transport: paramiko.Transport | None = None
        self._tunnel_server: socketserver.TCPServer | None = None
        self._tunnel_thread: threading.Thread | None = None

    def setup(self, progress_callback: Callable[[str], None] | None = None) -> str:
        """
        サーバーのセットアップ（デプロイ・起動・トンネル）

        Args:
            progress_callback: 進捗を通知するコールバック関数

        Returns:
            初期パス（ホームディレクトリ）
        """
        def report(msg: str):
            print(f"[DEBUG] {msg}", flush=True)
            if progress_callback:
                progress_callback(msg)

        # 1. SSH接続
        report("SSH接続中...")
        self._connect_ssh()

        # 2. 既存プロセスを停止（デプロイ前に必要）
        report("既存サーバーを停止中...")
        self._kill_server()

        # 3. デプロイ
        report("サーバーをデプロイ中...")
        self._deploy_binary()

        # 4. サーバー起動
        report("サーバーを起動中...")
        self._start_server()

        # 4. ポートフォワーディング
        report("トンネルを確立中...")
        self._start_tunnel()

        # 初期パス（ホームディレクトリ）を取得
        if not self.ssh:
            raise RuntimeError("SSH connection not established")
        _, stdout, _ = self.ssh.exec_command("echo $HOME")
        home_dir = stdout.read().decode().strip()

        return home_dir

    def _load_ssh_config(self) -> dict:
        """~/.ssh/configからホスト設定を読み込む"""
        config = paramiko.SSHConfig()
        with open(self.ssh_config_path) as f:
            config.parse(f)

        host_config = config.lookup(self.host)
        if not host_config:
            raise ValueError(f"Host '{self.host}' not found in ssh config")

        return host_config

    def _connect_ssh(self):
        """SSH接続を確立"""
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        config = self._load_ssh_config()

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

        self.transport = self.ssh.get_transport()

    def _deploy_binary(self):
        """バイナリをリモートに転送"""
        # ローカルバイナリの存在確認
        if not Path(self.LOCAL_BINARY).exists():
            raise FileNotFoundError(
                f"Binary not found: {self.LOCAL_BINARY}. Run 'make build' first."
            )

        sftp = self.ssh.open_sftp()

        # リモートディレクトリを作成
        remote_dir = self.REMOTE_DIR
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            # ディレクトリが存在しない場合は作成
            parts = remote_dir.split("/")
            current = ""
            for part in parts:
                current = f"{current}/{part}" if current else part
                try:
                    sftp.stat(current)
                except FileNotFoundError:
                    sftp.mkdir(current)

        # バイナリを転送
        remote_path = f"{remote_dir}/{self.REMOTE_BINARY}"
        sftp.put(self.LOCAL_BINARY, remote_path)

        # 実行権限を付与
        sftp.chmod(remote_path, 0o755)

        sftp.close()

    def _kill_server(self):
        """既存のサーバープロセスを停止"""
        if not self.ssh:
            raise RuntimeError("SSH connection not established")

        cmd = f"pkill -f {self.REMOTE_BINARY}"
        print(f"[DEBUG] exec: {cmd}", flush=True)
        _, stdout, stderr = self.ssh.exec_command(cmd)
        # コマンド完了を待つ
        stdout.read()
        stderr.read()

    def _start_server(self):
        """リモートでサーバーを起動"""
        if not self.ssh:
            raise RuntimeError("SSH connection not established")

        remote_path = f"{self.REMOTE_DIR}/{self.REMOTE_BINARY}"
        cmd = f"nohup ~/{remote_path} > /dev/null 2>&1 &"
        print(f"[DEBUG] exec: {cmd}", flush=True)
        self.ssh.exec_command(cmd)

    def _start_tunnel(self):
        """ローカルポートフォワーディングを開始"""
        transport = self.transport
        remote_host = "127.0.0.1"
        remote_port = self.REMOTE_PORT

        class ForwardHandler(socketserver.BaseRequestHandler):
            def handle(self):
                try:
                    channel = transport.open_channel(
                        "direct-tcpip",
                        (remote_host, remote_port),
                        self.request.getpeername(),
                    )
                except Exception:
                    return

                if channel is None:
                    return

                try:
                    while True:
                        # select で両方向を監視
                        r, _, _ = select.select([self.request, channel], [], [], 1.0)

                        if self.request in r:
                            data = self.request.recv(4096)
                            if len(data) == 0:
                                break
                            channel.send(data)

                        if channel in r:
                            data = channel.recv(4096)
                            if len(data) == 0:
                                break
                            self.request.send(data)
                except Exception:
                    pass
                finally:
                    channel.close()

        class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            daemon_threads = True
            allow_reuse_address = True

        self._tunnel_server = ThreadedTCPServer(
            ("127.0.0.1", self.LOCAL_PORT),
            ForwardHandler,
        )

        self._tunnel_thread = threading.Thread(
            target=self._tunnel_server.serve_forever,
            daemon=True,
        )
        self._tunnel_thread.start()

    def cleanup(self):
        """リソースのクリーンアップ"""
        # トンネルを停止
        if self._tunnel_server:
            self._tunnel_server.shutdown()
            self._tunnel_server = None

        # リモートサーバーをkill
        if self.ssh:
            try:
                self.ssh.exec_command(f"pkill -f {self.REMOTE_BINARY}")
            except Exception:
                pass

        # SSH接続を閉じる
        if self.ssh:
            try:
                self.ssh.close()
            except Exception:
                pass
            self.ssh = None
            self.transport = None
