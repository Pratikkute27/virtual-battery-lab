"""Entry point: run `python main.py` to start Virtual Battery Lab."""
import sys

from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> int:
    """Create the Qt application and show the main window."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())