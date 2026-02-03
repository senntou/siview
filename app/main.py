import os
import sys

import PySide6
from PySide6.QtWidgets import QApplication

from state.manager import StateManager
from ui.host_dialog import HostDialog
from ui.main_window import MainWindow


def main():
    # 環境変数にPySide6を登録
    dirname = os.path.dirname(PySide6.__file__)
    plugin_path = os.path.join(dirname, "plugins", "platforms")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

    app = QApplication(sys.argv)

    # ホスト名の決定: 前回のホスト > ダイアログ
    state = StateManager()
    last_host = state.get_last_host()

    if last_host:
        # 前回のホストがあれば自動選択
        host = last_host
    else:
        # なければダイアログを表示
        history = state.get_host_history()
        dialog = HostDialog(history)
        if dialog.exec() != HostDialog.DialogCode.Accepted:
            sys.exit(0)
        host = dialog.selected_host()
        if not host:
            sys.exit(0)

    window = MainWindow(host=host)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

