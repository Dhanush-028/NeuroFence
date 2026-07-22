"""
neuron_inspector_panel.py

A "deep-dive" panel widget for inspecting a specific layer/neuron's
activation distribution, plus the QThread pattern that keeps the rest of
the app responsive while it does the (potentially slow) tensor work.

Drop this into your PyQt app and wire it up like:

    from neuron_inspector_panel import NeuronInspectorPanel

    panel = NeuronInspectorPanel(get_activation_stats_fn=my_scan_backend.get_layer_stats)
    layout.addWidget(panel)

`get_activation_stats_fn(layer_name: str) -> dict` should be your existing
backend call that pulls activation stats for a layer — it's run on a
worker thread, not the GUI thread, so a slow lookup won't freeze the UI.

Requires: PyQt6 (adjust imports to PyQt5 if that's what your app uses).
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)


class ActivationStatsWorker(QThread):
    """Runs the (possibly slow) activation-stats lookup off the GUI thread."""

    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, fetch_fn, layer_name: str, parent=None):
        super().__init__(parent)
        self._fetch_fn = fetch_fn
        self._layer_name = layer_name

    def run(self):
        try:
            stats = self._fetch_fn(self._layer_name)
            self.finished.emit(stats)
        except Exception as exc:  # surface backend errors instead of crashing the thread silently
            self.failed.emit(str(exc))


class NeuronInspectorPanel(QWidget):
    """Deep-dive panel: pick a layer, inspect its neuron activation stats
    without blocking the rest of the desktop app."""

    def __init__(self, get_activation_stats_fn, layer_names: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._get_activation_stats_fn = get_activation_stats_fn
        self._worker: ActivationStatsWorker | None = None

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Layer:"))
        self.layer_picker = QComboBox()
        if layer_names:
            self.layer_picker.addItems(layer_names)
        header.addWidget(self.layer_picker, stretch=1)

        self.inspect_btn = QPushButton("Inspect")
        self.inspect_btn.clicked.connect(self._on_inspect_clicked)
        header.addWidget(self.inspect_btn)
        root.addLayout(header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate spinner
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #cf222e;")
        self.status_label.setVisible(False)
        root.addWidget(self.status_label)

        self.stats_table = QTableWidget(0, 2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(self.stats_table)

    def set_layer_names(self, layer_names: list[str]):
        self.layer_picker.clear()
        self.layer_picker.addItems(layer_names)

    def _on_inspect_clicked(self):
        layer_name = self.layer_picker.currentText()
        if not layer_name:
            return

        self.inspect_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setVisible(False)
        self.stats_table.setRowCount(0)

        self._worker = ActivationStatsWorker(self._get_activation_stats_fn, layer_name, self)
        self._worker.finished.connect(self._on_stats_ready)
        self._worker.failed.connect(self._on_stats_failed)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_stats_ready(self, stats: dict):
        self.progress.setVisible(False)
        self.inspect_btn.setEnabled(True)

        self.stats_table.setRowCount(len(stats))
        for row, (metric, value) in enumerate(stats.items()):
            self.stats_table.setItem(row, 0, QTableWidgetItem(str(metric)))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _on_stats_failed(self, message: str):
        self.progress.setVisible(False)
        self.inspect_btn.setEnabled(True)
        self.status_label.setText(f"Failed to load stats: {message}")
        self.status_label.setVisible(True)


if __name__ == "__main__":
    import sys
    import random
    import time
    from PyQt6.QtWidgets import QApplication

    def fake_backend(layer_name: str) -> dict:
        time.sleep(1.2)  # simulate a slow tensor scan; UI stays responsive because this runs on a QThread
        return {
            "mean_activation": round(random.uniform(-0.1, 0.1), 4),
            "std_activation": round(random.uniform(0.5, 1.5), 4),
            "max_z_score": round(random.uniform(0, 9), 2),
            "num_neurons": random.randint(512, 4096),
        }

    app = QApplication(sys.argv)
    win = NeuronInspectorPanel(fake_backend, layer_names=["layer1.mlp", "layer2.attn", "layer4.attn.212"])
    win.setWindowTitle("Neuron Inspector — demo")
    win.resize(480, 320)
    win.show()
    sys.exit(app.exec())