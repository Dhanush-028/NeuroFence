"""
NeuroFence - Week 1 (Sandbox + Metadata) + Week 2 Day 3 (Heatmap)
Desktop UI (PyQt5).

Week 1 goal: "Initialize a local desktop application. Create views for
uploading model files and displaying basic metadata."

Week 2 goal (this addition): "Build a visual matrix in the UI (like a
heatmap) representing the active vs. dormant neurons in the model."

Run with: python desktop_ui.py
"""
import sys
import json
import os
from sandbox_loader import load_model_safely, get_model_metadata
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QTextEdit, QFileDialog, QLineEdit, QHBoxLayout, QTabWidget,
    QComboBox, QScrollArea, QGridLayout
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class NeuroFenceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.tokenizer = None
        self.activation_data = None  # loaded from baseline_activations.json
        self.setWindowTitle("NeuroFence - LLM Backdoor Scanner")
        self.resize(700, 520)
        self._build_ui()

    def _build_ui(self):
        outer_layout = QVBoxLayout()

        title = QLabel("NeuroFence — Model Forensic Sandbox")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        outer_layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_sandbox_tab(), "Sandbox")
        tabs.addTab(self._build_heatmap_tab(), "Neuron Heatmap")
        outer_layout.addWidget(tabs)

        self.setLayout(outer_layout)

    # --- Tab 1: Week 1 sandbox/metadata view (unchanged logic) ---------

    def _build_sandbox_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        input_row = QHBoxLayout()
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText(
            "HuggingFace model name (e.g. sshleifer/tiny-gpt2) or local model folder path"
        )
        self.model_input.setText("sshleifer/tiny-gpt2")
        input_row.addWidget(self.model_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.on_browse)
        input_row.addWidget(browse_btn)

        load_btn = QPushButton("Load Model")
        load_btn.clicked.connect(self.on_load_model)
        input_row.addWidget(load_btn)
        layout.addLayout(input_row)

        self.status_label = QLabel("No model loaded.")
        layout.addWidget(self.status_label)

        self.metadata_box = QTextEdit()
        self.metadata_box.setReadOnly(True)
        layout.addWidget(self.metadata_box)

        tab.setLayout(layout)
        return tab

    def on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Local Model Folder")
        if folder:
            self.model_input.setText(folder)
            self.status_label.setText(f"Selected local folder: {folder}")

    def on_load_model(self):
        model_source = self.model_input.text().strip()
        if not model_source:
            self.status_label.setText("Enter a model name or select a local folder first.")
            return
        self.status_label.setText(f"Loading {model_source} ... (check console for progress)")
        QApplication.processEvents()
        try:
            self.model, self.tokenizer = load_model_safely(model_source)
            meta = get_model_metadata(self.model)
            self.status_label.setText(f"Loaded: {model_source}")
            display_text = "\n".join(f"{k}: {v}" for k, v in meta.items())
            self.metadata_box.setPlainText(display_text)
        except Exception as e:
            self.status_label.setText("Failed to load model.")
            self.metadata_box.setPlainText(str(e))

    # --- Tab 2: Week 2 Day 3 heatmap view -------------------------------

    def _build_heatmap_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        controls_row = QHBoxLayout()

        load_json_btn = QPushButton("Load baseline_activations.json")
        load_json_btn.clicked.connect(lambda: self.on_load_activation_json())
        controls_row.addWidget(load_json_btn)

        controls_row.addWidget(QLabel("Category:"))
        self.category_dropdown = QComboBox()
        self.category_dropdown.currentTextChanged.connect(self.on_selection_changed)
        controls_row.addWidget(self.category_dropdown)

        controls_row.addWidget(QLabel("Layer:"))
        self.layer_dropdown = QComboBox()
        self.layer_dropdown.currentTextChanged.connect(self.on_selection_changed)
        controls_row.addWidget(self.layer_dropdown)

        layout.addLayout(controls_row)

        self.heatmap_status = QLabel(
            "No activation data loaded. Run fuzzer.py first to generate baseline_activations.json, "
            "then click the button above."
        )
        layout.addWidget(self.heatmap_status)

        # Scroll area in case a layer has many neurons - grid could get wide
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.heatmap_grid_container = QWidget()
        self.heatmap_grid = QGridLayout()
        self.heatmap_grid_container.setLayout(self.heatmap_grid)
        scroll.setWidget(self.heatmap_grid_container)
        layout.addWidget(scroll)

        tab.setLayout(layout)
        return tab

    def on_load_activation_json(self, path="baseline_activations.json"):
        if not os.path.exists(path):
            self.heatmap_status.setText(
                f"'{path}' not found in this folder. Run fuzzer.py first to generate it."
            )
            return
        try:
            with open(path, "r") as f:
                self.activation_data = json.load(f)
        except Exception as e:
            self.heatmap_status.setText(f"Failed to load {path}: {e}")
            return

        self.category_dropdown.blockSignals(True)
        self.category_dropdown.clear()
        self.category_dropdown.addItems(list(self.activation_data.keys()))
        self.category_dropdown.blockSignals(False)

        self._refresh_layer_dropdown()
        self.heatmap_status.setText(f"Loaded {path}. Pick a category and layer to view.")
        self.on_selection_changed()

    def _refresh_layer_dropdown(self):
        if not self.activation_data:
            return
        category = self.category_dropdown.currentText()
        if category not in self.activation_data:
            return
        layers = list(self.activation_data[category].keys())
        self.layer_dropdown.blockSignals(True)
        self.layer_dropdown.clear()
        self.layer_dropdown.addItems(layers)
        self.layer_dropdown.blockSignals(False)

    def on_selection_changed(self):
        if not self.activation_data:
            return
        self._refresh_layer_dropdown()
        category = self.category_dropdown.currentText()
        layer = self.layer_dropdown.currentText()
        if not category or not layer:
            return
        try:
            neuron_data = self.activation_data[category][layer]
            self._render_heatmap(neuron_data["mean_per_neuron"])
        except KeyError as e:
            self.heatmap_status.setText(f"Missing expected data: {e}")

    def _render_heatmap(self, values):
        """
        Draws one colored cell per neuron. Color intensity is scaled
        relative to the min/max of THIS layer's values, so a "dormant"
        neuron (near 0 relative to its peers) shows dark/blue and an
        "active" neuron shows bright/red. This is a first pass - Week 3
        will build on this to flag neurons that are unusually active
        ONLY on trigger-style prompts.
        """
        # Clear any previous cells
        while self.heatmap_grid.count():
            item = self.heatmap_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not values:
            self.heatmap_status.setText("This layer has no neuron data.")
            return

        lo, hi = min(values), max(values)
        span = (hi - lo) or 1.0  # avoid divide-by-zero if all values are equal

        columns = 32  # wrap into rows of 32 cells so wide layers stay readable
        for i, val in enumerate(values):
            normalized = (val - lo) / span  # 0.0 (dormant) to 1.0 (most active)
            color = self._activation_to_color(normalized)

            cell = QLabel()
            cell.setFixedSize(18, 18)
            cell.setToolTip(f"Neuron {i}: {val:.4f}")
            cell.setStyleSheet(
                f"background-color: rgb({color.red()},{color.green()},{color.blue()}); "
                f"border: 1px solid #333;"
            )
            row, col = divmod(i, columns)
            self.heatmap_grid.addWidget(cell, row, col)

        self.heatmap_status.setText(
            f"{len(values)} neurons shown. Range: {lo:.4f} to {hi:.4f}. Hover a cell for exact value."
        )

    @staticmethod
    def _activation_to_color(normalized: float) -> QColor:
        """Simple blue (dormant) -> red (active) gradient."""
        normalized = max(0.0, min(1.0, normalized))
        r = int(255 * normalized)
        b = int(255 * (1 - normalized))
        return QColor(r, 60, b)


def main():
    app = QApplication(sys.argv)
    window = NeuroFenceWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()