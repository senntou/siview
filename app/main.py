import PySide6
import os
import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


if __name__ == "__main__":
    # 環境変数にPySide6を登録
    dirname = os.path.dirname(PySide6.__file__)
    plugin_path = os.path.join(dirname, 'plugins', 'platforms')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
    
    app = QApplication(sys.argv)    # PySide6の実行
    window = MainWindow()
    window.show()                   # PySide6のウィンドウを表示
    sys.exit(app.exec())            # PySide6の終了

