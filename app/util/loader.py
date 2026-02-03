from pathlib import Path

# appディレクトリを基準にする
APP_DIR = Path(__file__).parent.parent


def load_stylesheet(path: str) -> str:
    """スタイルシートを読み込む（パスはui/からの相対パス）"""
    full_path = APP_DIR / "ui" / path
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()
