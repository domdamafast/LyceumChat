import sys
import sqlite3

sys.dont_write_bytecode = True

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMessageBox

from window import ChatWindow


# Создаёт приложение, открывает окно чата и запускает обработку событий
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Лицей Чат")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 11))
    try:
        window = ChatWindow()
    except (OSError, ValueError, sqlite3.Error) as error:
        QMessageBox.critical(None, "Не удалось открыть программу", str(error))
        return 1
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
