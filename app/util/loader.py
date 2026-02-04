from pathlib import Path
import os
import sys

# appディレクトリを基準にする
APP_DIR = Path(__file__).parent.parent


def load_stylesheet(path: str) -> str:
    """スタイルシートを読み込む（パスはui/からの相対パス）"""
    full_path = APP_DIR / "ui" / path
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

def resource_path(relative_path) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path) # type: ignore
    return os.path.join(os.path.abspath("."), relative_path)

