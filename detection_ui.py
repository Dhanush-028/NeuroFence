"""
NeuroFence - Week 3
Detection UI: same heatmap as Week 2, but the flagged neuron(s) get a red
outline so an analyst can immediately see which neuron tripped the alarm.
"""

import sys
import json
from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QRect

CELL_SIZE = 14
MAX_NEURONS_SHOWN = 64


def normalize(values):
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def value_to_color(v):
    r = int(11 + v * (2 - 11))
    g = int(31 + v * (195 - 31))
    b = int(38 + v * (154 - 38))
    return QColor(max(0, r), max(0, g), max(0, b))


class DetectionHeatmap(QWidget):
    def __init__(self, baseline_data, flagged_cells):
        super().__init__()
        self.layers = baseline_data["layers"]
        self.layer_names = list(self.layers.keys())
        # flagged_cells: set of (layer_name, neuron_index)
        self.flagged_cells = flagged_cells
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
                x = label_width + col * CELL_SIZE
                y = row * CELL_SIZE
                painter.fillRect(x, y, CELL_SIZE - 1, CELL_SIZE - 1, value_to_color(v))

                if (layer_name, col) in self.flagged_cells:
                    pen = QPen(QColor(230, 60, 60))
                    pen.setWidth(2)
                    painter.setPen(pen)
                    painter.drawRect(x, y, CELL_SIZE - 1, CELL_SIZE - 1)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def main():
    app = QApplication(sys.argv)

    baseline = load_json("activation_baseline.json")
    report = load_json("detection_report.json")

    flagged_cells = {
        (f["layer"], f["neuron"])
        for f in report["top_findings"]
        if f["z_score"] >= report["z_score_threshold"]
    }

    window = QWidget()
    window.setWindowTitle("NeuroFence - Backdoor Detection Result")
    layout = QVBoxLayout()

    header = QLabel(
        f"Flagged neurons: {len(flagged_cells)}  |  Threshold: z >= {report['z_score_threshold']}  |  "
        f"Red outline = anomalous neuron"
    )
    layout.addWidget(header)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(DetectionHeatmap(baseline, flagged_cells))
    layout.addWidget(scroll)

    window.setLayout(layout)
    window.resize(1000, 500)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
