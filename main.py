import argparse
import sys
from PyQt6.QtWidgets import QApplication
from controller import SignalViewerController
from model import RedisClient
from view import MainWindow

if __name__ == "__main__":
    # setup argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--x_dynamic", action="store_true", help="Enable dynamic x-axis")
    args = parser.parse_args()

    # create QApplication
    app = QApplication(sys.argv)
    controller = SignalViewerController(
        RedisClient(),
        MainWindow(),
        x_dynamic=args.x_dynamic
    )
    controller.view.show()
    sys.exit(app.exec())
