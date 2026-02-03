import argparse
import os
import sys
from pathlib import Path

import PySide6
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def load_dotenv():
    """プロジェクトルートの.envファイルを読み込む"""
    # app/main.py -> プロジェクトルート
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"

    if not env_file.exists():
        return

    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="SIView - Remote Image Viewer")
    parser.add_argument("host", nargs="?", help="SSH host name (from ~/.ssh/config)")
    args = parser.parse_args()

    # ホスト名の決定: 引数 > 環境変数
    host = args.host or os.environ.get("SIVIEW_HOST_NAME")
    if not host:
        parser.error("host is required (or set SIVIEW_HOST_NAME)")

    # 環境変数にPySide6を登録
    dirname = os.path.dirname(PySide6.__file__)
    plugin_path = os.path.join(dirname, "plugins", "platforms")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

    app = QApplication(sys.argv)
    window = MainWindow(host=host)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

