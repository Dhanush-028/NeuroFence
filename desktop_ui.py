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

        controls_row.addStretch()
        layout.addLayout(controls_row)

        self.heatmap_status = QLabel(
            "No activation data loaded. Run fuzzer.py first to generate baseline_activations.json, "
            "then click the button above."
        )
        layout.addWidget(self.heatmap_status)

        # Scroll area since with many layers x many neurons the grid gets big
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.heatmap_grid_container = QWidget()
        self.heatmap_grid = QGridLayout()
        self.heatmap_grid.setSpacing(1)
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

        self.heatmap_status.setText(f"Loaded {path}. Showing all layers for the selected category.")
        self.on_selection_changed()

    def on_selection_changed(self):
        if not self.activation_data:
            return
        category = self.category_dropdown.currentText()
        if not category or category not in self.activation_data:
            return
        self._render_all_layers_heatmap(self.activation_data[category])

    def _render_all_layers_heatmap(self, layers_dict, max_neurons_per_row: int = 40):
        # Clear any previous cells
        while self.heatmap_grid.count():
            item = self.heatmap_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not layers_dict:
            self.heatmap_status.setText("No layers in this category.")
            return

        # Compute global min/max across every neuron in every layer first,
        # so color scale is consistent across the whole grid.
        all_values = []
        for layer_summary in layers_dict.values():
            all_values.extend(layer_summary.get("mean_per_neuron", []))
        if not all_values:
            self.heatmap_status.setText("No neuron data found in this category.")
            return
        lo, hi = min(all_values), max(all_values)
        span = (hi - lo) or 1.0

        truncated_layers = 0
        for row, (layer_name, layer_summary) in enumerate(layers_dict.items()):
            # Row label = layer name
            label = QLabel(layer_name)
            label.setStyleSheet("font-size: 10px;")
            label.setFixedWidth(160)
            self.heatmap_grid.addWidget(label, row, 0)

            values = layer_summary.get("mean_per_neuron", [])
            shown_values = values[:max_neurons_per_row]
            if len(values) > max_neurons_per_row:
                truncated_layers += 1

            for col, val in enumerate(shown_values, start=1):
                normalized = (val - lo) / span
                color = self._activation_to_color(normalized)
                cell = QLabel()
                cell.setFixedSize(14, 14)
                cell.setToolTip(f"{layer_name}\nNeuron {col - 1}: {val:.4f}")
                cell.setStyleSheet(
                    f"background-color: rgb({color.red()},{color.green()},{color.blue()}); "
                    f"border: 1px solid #222;"
                )
                self.heatmap_grid.addWidget(cell, row, col)

        status = (
            f"{len(layers_dict)} layers shown, up to {max_neurons_per_row} neurons per row. "
            f"Global range: {lo:.4f} to {hi:.4f}. Hover a cell for exact value."
        )
        if truncated_layers:
            status += f" ({truncated_layers} layer(s) have more neurons than shown - truncated for display.)"
        self.heatmap_status.setText(status)

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