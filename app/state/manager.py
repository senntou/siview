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

    def __init__(self, host: str):
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
        if self.host not in self._state:
            self._state[self.host] = {}

        self._state[self.host]["current_dir"] = path
        self._save()
