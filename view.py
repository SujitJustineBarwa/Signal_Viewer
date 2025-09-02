from PyQt6 import QtCore
from PyQt6.QtWidgets import (QVBoxLayout,QHBoxLayout,                                   # Layouts import
                              QListWidget, QWidget,QMainWindow,QApplication,QTabWidget, # Main widgets
                              QLabel,QPushButton,QMenu,QLineEdit)                       # Subwidgets
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import QDataStream, Qt, QVariant

import pyqtgraph as pg
from pyqtgraph.graphicsItems.DateAxisItem import DateAxisItem
import datetime
import numpy as np
import colorsys
import time
import sys
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"


# We cannot use QListWidget directly in StreamListWidget because it then converts the listed items into a file format
# called application/x-qabstractitemmodeldatalist.Hence, the sub-class is used so as to tell the list widget to also
# store plain text in its drag data.This drag data is used to pass the signal name to the plot widget.
class StreamList(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)   # enable dragging

    def mimeData(self, items):
        """Called when user starts dragging items."""
        md = super().mimeData(items)   # get default mime data (Qt's format)

        if items:
            # Add text/plain to the MIME data
            md.setText(items[0].text())   # e.g., "apple"
        return md

class StreamListWidget(QWidget):
    """Shows available streams, supports drag, with search."""
    def __init__(self):
        super().__init__()

        # Widgets
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Signal ...")
        self.refresh_button = QPushButton("Refresh")
        self.stream_list = StreamList()

        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("Available Signals"))
        self.layout.addWidget(self.search_bar)
        self.layout.addWidget(self.stream_list)
        self.layout.addWidget(self.refresh_button)

        # Connect search functionality
        self.search_bar.textChanged.connect(self.filter_streams)

        # Internal storage of all signals
        self._all_signals = []

    def update_signals(self, signals):
        """Update list with all available signals."""
        self._all_signals = signals
        self.apply_filter()

    def filter_streams(self, text):
        """Filter list based on search text."""
        self.apply_filter(text)

    def apply_filter(self, text=""):
        """Apply search filter to the list."""
        self.stream_list.clear()
        if text:
            filtered = [s for s in self._all_signals if text.lower() in s.lower()]
        else:
            filtered = self._all_signals
        self.stream_list.addItems(filtered)

class PlotWidget(pg.PlotWidget):
    """Single plot, supports multiple signals overlayed."""

    # Signals to delegate menu actions back to PlotAreaWidget
    addPlotAbove = pyqtSignal(object)   # emit self
    addPlotBelow = pyqtSignal(object)
    deletePlot = pyqtSignal(object)
    plot_status = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.plot_id = str(int(time.time()))
        self.curves = {}
        self.showGrid(x=True, y=True)
        self.addLegend()
        self.plotItem.setAcceptDrops(True) # Enable drops on the PlotItem (seach in google : How to accept drop in pg.PlotWidget)

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        signal_name = event.mimeData().text()
        self.update_signal(signal_name, x=[], y=[])

    def update_signal(self, stream_name: str, x, y, x_dynamic=False):

        if x:  # non-empty
            if isinstance(x[0], datetime.datetime):
                if not x_dynamic:
                    x = [idx for idx, dt in enumerate(x)]
                else:
                    x = [dt.timestamp() for dt in x]

                    # Create DateAxis with grid enabled
                    date_axis = DateAxisItem(orientation='bottom')
                    date_axis.setGrid(100)  # turn on grid lines
                    date_axis.setPen(pg.mkPen(color='w'))  # axis line
                    date_axis.setTickFont(self.font())   # keep ticks readable
                    self.plotItem.setAxisItems({'bottom': date_axis})

        if stream_name not in self.curves:
            curve = self.plot(pen=pg.mkPen(width=2, color=self.generate_random_rgb_color()), name=stream_name)
            self.curves[stream_name] = curve
        self.curves[stream_name].setData(x, y)
        self.plot_status.emit(self)

    def generate_random_rgb_color(self):
        h = np.random.rand()
        s = 0.7 + 0.3 * np.random.rand()
        v = 0.9 + 0.1 * np.random.rand()
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))

    def handle_remove_signal(self, stream_name: str):
        if stream_name in self.curves:
            self.removeItem(self.curves[stream_name])
            del self.curves[stream_name]
            self.plot_status.emit(self)

    def handle_clear_all(self):
        self.clear()
        self.curves.clear()
        self.plot_status.emit(self)

    def contextMenuEvent(self, event):

        # Instead of handling logic here, emit signals
        menu = QMenu(self)

        add_plot_above = QAction("Add plot above", self)
        add_plot_above.triggered.connect(lambda: self.addPlotAbove.emit(self))
        menu.addAction(add_plot_above)

        add_plot_below = QAction("Add plot below", self)
        add_plot_below.triggered.connect(lambda: self.addPlotBelow.emit(self))
        menu.addAction(add_plot_below)

        clear_all = QAction("Clear all signals", self)
        clear_all.triggered.connect(lambda: self.handle_clear_all())
        menu.addAction(clear_all)

        delete_plot = QAction("Delete plot", self)
        delete_plot.triggered.connect(lambda: self.deletePlot.emit(self))
        menu.addAction(delete_plot)

        # Submenu for removing individual signals
        remove_sig_menu = QMenu("Remove Signal", self)
        for stream_name in list(self.curves.keys()):
            action = QAction(f"Remove {stream_name}", self)
            action.triggered.connect(
                lambda checked, sn=stream_name: self.handle_remove_signal(sn)
            )
            remove_sig_menu.addAction(action)

        menu.addMenu(remove_sig_menu)
        menu.exec(event.globalPos())


class PlotAreaWidget(QWidget):
    """Manages vertical stack of PlotWidgets."""

    plotsChanged = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(QLabel("Signal Plots"))
        self.layout = QVBoxLayout()
        self.main_layout.addLayout(self.layout)
        self.plot_widgets = []
        self.manage_plots()  # start with one

    def manage_plots(self, index=None):
        pw = PlotWidget()

        # Connect plot signals to area logic
        pw.addPlotAbove.connect(self.handle_add_plot_above)
        pw.addPlotBelow.connect(self.handle_add_plot_below)
        pw.deletePlot.connect(self.handle_delete_plot)
        pw.plot_status.connect(self.handle_plot_status)

        if index is None:
            self.layout.addWidget(pw)
            self.plot_widgets.append(pw)
        else:
            self.layout.insertWidget(index, pw)
            self.plot_widgets.insert(index, pw)

    def handle_plot_status(self, plot):
        self.plotsChanged.emit(self.plot_widgets)

    def handle_add_plot_above(self, plot):
        index = self.plot_widgets.index(plot)
        self.manage_plots(index)
    
    def handle_add_plot_below(self, plot):
        index = self.plot_widgets.index(plot) + 1
        self.manage_plots(index)

    def handle_delete_plot(self, plot):
        self.plot_widgets.remove(plot)
        plot.deleteLater()
        if self.plot_widgets == []:
            self.manage_plots()
        self.plotsChanged.emit(self.plot_widgets)

class MainWindow(QMainWindow):
    """Overall application window (contains StreamList + PlotArea)."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Signal Viewer")
        self.resize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)

        self.stream_list = StreamListWidget()
        layout.addWidget(self.stream_list, 1)

        self.plot_area = PlotAreaWidget()
        layout.addWidget(self.plot_area, 4)


# Uncomment this to see streaming updates
# Run it after running the signal emitter.py
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())