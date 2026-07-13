"""
NeuroFence - Week 2
Heatmap: draws a grid of layers x neurons, colored by mean activation.
Pure PyQt painting - no matplotlib, keeps things light and native.
"""

import sys
import json
from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt, QRect

CELL_SIZE = 14
MAX_NEURONS_SHOWN = 64  # cap columns so wide hidden_size models stay readable


def normalize(values):
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def value_to_color(v):
    # low activation -> dark navy, high activation -> bright teal/mint
    r = int(11 + v * (2 - 11))
    g = int(31 + v * (195 - 31))
    b = int(38 + v * (154 - 38))
    return QColor(max(0, r), max(0, g), max(0, b))


class HeatmapWidget(QWidget):
    def __init__(self, baseline_data):
        super().__init__()
        self.layers = baseline_data["layers"]
        self.layer_names = list(self.layers.keys())
        self.setMinimumSize(
            CELL_SIZE * MAX_NEURONS_SHOWN + 220,
            CELL_SIZE * max(1, len(self.layer_names)) + 40,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        label_width = 200
        for row, layer_name in enumerate(self.layer_names):
            stats = self.layers[layer_name]
            means = stats["mean_per_neuron"]
            if not isinstance(means, list):
                means = [means]
            means = means[:MAX_NEURONS_SHOWN]
            norm = normalize(means)

            painter.setPen(QColor(30, 36, 48))
            painter.drawText(QRect(0, row * CELL_SIZE, label_width - 10, CELL_SIZE),
                              Qt.AlignRight | Qt.AlignVCenter, layer_name)

            for col, v in enumerate(norm):
                color = value_to_color(v)
                painter.fillRect(
                    label_width + col * CELL_SIZE, row * CELL_SIZE,
                    CELL_SIZE - 1, CELL_SIZE - 1, color,
                )


def load_baseline(path="activation_baseline.json"):
    with open(path) as f:
        return json.load(f)


def main():
    app = QApplication(sys.argv)

    baseline = load_baseline()

    window = QWidget()
    window.setWindowTitle("NeuroFence - Neuron Activity Heatmap")
    layout = QVBoxLayout()

    header = QLabel(
        f"Model: {baseline['model_name']}  |  Prompts fuzzed: {baseline['num_prompts']}  |  "
        f"Layers shown: {len(baseline['layers'])} (darker = lower activation, brighter = higher)"
    )
    layout.addWidget(header)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(HeatmapWidget(baseline))
    layout.addWidget(scroll)

    window.setLayout(layout)
    window.resize(1000, 500)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
