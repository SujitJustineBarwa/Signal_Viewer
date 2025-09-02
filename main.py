from PyQt6.QtWidgets import QApplication
from controller import SignalViewerController
from model import RedisClient
from view import MainWindow
import threading
import os
import sys

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    controller = SignalViewerController(RedisClient(), MainWindow())
    controller.view.show()
    sys.exit(app.exec())