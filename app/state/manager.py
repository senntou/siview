"""
アプリケーション状態の永続化

~/.siview/state.json に状態を保存
"""

import json
from pathlib import Path


class StateManager:
    """ホストごとの状態を管理"""

    STATE_DIR = Path.home() / ".siview"
    STATE_FILE = STATE_DIR / "state.json"

    # グローバル状態用のキー
    _GLOBAL_KEY = "_global"
    _LAST_HOST_KEY = "last_host"
    _HOST_HISTORY_KEY = "host_history"

    def __init__(self, host: str | None = None):
        self.host = host
        self._state = self._load()

    def _load(self) -> dict:
        """状態ファイルを読み込む"""
        if not self.STATE_FILE.exists():
            return {}

        try:
            with open(self.STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save(self):
        """状態ファイルに保存"""
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)

        with open(self.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)

    def get_current_dir(self) -> str | None:
        """保存されたカレントディレクトリを取得"""
        host_state = self._state.get(self.host, {})
        return host_state.get("current_dir")

    def set_current_dir(self, path: str):
        """カレントディレクトリを保存"""
        if self.host is None:
            return

        if self.host not in self._state:
            self._state[self.host] = {}

        self._state[self.host]["current_dir"] = path
        self._save()

    # --- グローバル状態（ホスト非依存） ---

    def get_last_host(self) -> str | None:
        """最後に使用したホスト名を取得"""
        global_state = self._state.get(self._GLOBAL_KEY, {})
        return global_state.get(self._LAST_HOST_KEY)

    def set_last_host(self, host: str):
        """最後に使用したホスト名を保存"""
        if self._GLOBAL_KEY not in self._state:
            self._state[self._GLOBAL_KEY] = {}

        self._state[self._GLOBAL_KEY][self._LAST_HOST_KEY] = host
        self._add_to_history(host)
        self._save()

    def get_host_history(self) -> list[str]:
        """ホスト名の履歴を取得（最新順）"""
        global_state = self._state.get(self._GLOBAL_KEY, {})
        return global_state.get(self._HOST_HISTORY_KEY, [])

    def _add_to_history(self, host: str):
        """ホスト名を履歴に追加（最新を先頭に、重複は削除）"""
        if self._GLOBAL_KEY not in self._state:
            self._state[self._GLOBAL_KEY] = {}

        history = self._state[self._GLOBAL_KEY].get(self._HOST_HISTORY_KEY, [])

        # 既存のものを削除して先頭に追加
        if host in history:
            history.remove(host)
        history.insert(0, host)

        # 最大10件まで保持
        self._state[self._GLOBAL_KEY][self._HOST_HISTORY_KEY] = history[:10]
