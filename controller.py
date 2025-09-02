from PyQt6.QtCore import QObject, QThread, pyqtSignal
from view import MainWindow
from model import RedisClient,RedisWorker

class SignalViewerController:
    def __init__(self, model: RedisClient, view: MainWindow):
        self.model = model
        self.view = view

        # Update signal list
        self.view.stream_list.refresh_button.clicked.connect(self.update_signal_list)
        self.update_signal_list()

        # Track plots
        self.view.plot_area.plotsChanged.connect(self.handle_plot_status)
        self.plot_signal_map = {}

        # Track active subscriptions
        self.subscribed_signals = set()

    def update_signal_list(self):
        all_signals = self.model.list_streams()
        self.view.stream_list.update_signals(all_signals)

    def handle_plot_status(self, plotList):
        """Called whenever plots are added/removed/changed."""
        new_subscribed_signals = set()
        new_plot_signal_map = {}

        for plot in plotList:
            signals_in_plot = list(plot.curves.keys())
            new_plot_signal_map[plot] = signals_in_plot
            new_subscribed_signals.update(signals_in_plot)

        added = new_subscribed_signals - self.subscribed_signals
        removed = self.subscribed_signals - new_subscribed_signals

        for signal_name in added:
            self.model.subscribe(signal_name, self.subscription_callback)

        for signal_name in removed:
            self.model.unsubscribe(signal_name)

        self.subscribed_signals = new_subscribed_signals
        self.plot_signal_map = new_plot_signal_map

    def subscription_callback(self, signal_name, signal_queue):
        """Update plots safely in the main Qt thread."""
        for plot, signal_list in self.plot_signal_map.items():
            if signal_name in signal_list:
                # Extract x and y data from the signal_queue
                x = [item["timestamp"] for item in signal_queue]
                y = [item["value"] for item in signal_queue]
                plot.update_signal(signal_name, x, y)