import sys
from PyQt5.QtWidgets import QApplication
from gui import RenamerApp


def main():
    app = QApplication(sys.argv)

    window = RenamerApp()
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())