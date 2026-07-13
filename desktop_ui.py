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
        tabs.addTab(self._build_diff_tab(), "Category Diff")
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

        # Also populate the Category Diff tab's two dropdowns
        categories = list(self.activation_data.keys())
        for dropdown in (self.diff_category_a, self.diff_category_b):
            dropdown.blockSignals(True)
            dropdown.clear()
            dropdown.addItems(categories)
            dropdown.blockSignals(False)
        # Default to a sensible comparison if both categories exist:
        # trigger-style prompts vs normal ones is the actual forensic question.
        if "trigger_style" in categories:
            self.diff_category_a.setCurrentText("trigger_style")
        if "normal" in categories:
            self.diff_category_b.setCurrentText("normal")

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
        
        normalized = max(0.0, min(1.0, normalized))
        r = int(255 * normalized)
        b = int(255 * (1 - normalized))
        return QColor(r, 60, b)

    # --- Tab 3: Week 2 Day 5 - compare two categories, flag outliers ---
    #
    # This is the actual forensic point of the whole project: a normal
    # neuron should behave roughly the same regardless of prompt category.
    # A BACKDOORED neuron is expected to behave close to normal on
    # everyday text, but spike sharply and specifically on its trigger
    # phrase. So the neurons worth investigating are the ones with the
    # biggest gap between "trigger_style" and "normal" activation - not
    # necessarily the most active neurons overall.
    #
    # This tab doesn't claim to detect real backdoors yet (that needs a
    # properly trained backdoored model to test against, plus a real
    # statistical threshold - that's Week 3). What it does is surface the
    # comparison itself, which is the building block Week 3 needs.

    def _build_diff_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("Compare:"))
        self.diff_category_a = QComboBox()
        controls_row.addWidget(self.diff_category_a)
        controls_row.addWidget(QLabel("vs."))
        self.diff_category_b = QComboBox()
        controls_row.addWidget(self.diff_category_b)

        compare_btn = QPushButton("Show Difference")
        compare_btn.clicked.connect(lambda: self.on_show_diff())
        controls_row.addWidget(compare_btn)
        controls_row.addStretch()
        layout.addLayout(controls_row)

        self.diff_status = QLabel(
            "Load activation data in the Neuron Heatmap tab first, then pick two "
            "categories here and click 'Show Difference'."
        )
        layout.addWidget(self.diff_status)

        layout.addWidget(QLabel("Top neurons by activation difference (most suspicious first):"))
        self.diff_flagged_list = QTextEdit()
        self.diff_flagged_list.setReadOnly(True)
        self.diff_flagged_list.setMaximumHeight(140)
        layout.addWidget(self.diff_flagged_list)

        layout.addWidget(QLabel("Difference heatmap (red = higher on category A, blue = higher on category B):"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.diff_grid_container = QWidget()
        self.diff_grid = QGridLayout()
        self.diff_grid.setSpacing(1)
        self.diff_grid_container.setLayout(self.diff_grid)
        scroll.setWidget(self.diff_grid_container)
        layout.addWidget(scroll)

        tab.setLayout(layout)
        return tab

    def on_show_diff(self):
        if not self.activation_data:
            self.diff_status.setText("No activation data loaded yet - load it in the Neuron Heatmap tab first.")
            return

        cat_a = self.diff_category_a.currentText()
        cat_b = self.diff_category_b.currentText()
        if not cat_a or not cat_b:
            self.diff_status.setText("Pick two categories to compare.")
            return
        if cat_a == cat_b:
            self.diff_status.setText("Pick two DIFFERENT categories to compare.")
            return
        if cat_a not in self.activation_data or cat_b not in self.activation_data:
            self.diff_status.setText("Selected category not found in loaded data.")
            return

        layers_a = self.activation_data[cat_a]
        layers_b = self.activation_data[cat_b]

        # Only compare layers/neuron counts that exist in both categories -
        # they should match since both ran through the same model, but we
        # guard against mismatches rather than crashing.
        diffs_per_layer = {}
        flagged = []  # (abs_diff, layer_name, neuron_index, val_a, val_b, diff)

        for layer_name in layers_a:
            if layer_name not in layers_b:
                continue
            values_a = layers_a[layer_name].get("mean_per_neuron", [])
            values_b = layers_b[layer_name].get("mean_per_neuron", [])
            n = min(len(values_a), len(values_b))

            layer_diffs = []
            for i in range(n):
                diff = values_a[i] - values_b[i]
                layer_diffs.append(diff)
                flagged.append((abs(diff), layer_name, i, values_a[i], values_b[i], diff))

            diffs_per_layer[layer_name] = layer_diffs

        if not diffs_per_layer:
            self.diff_status.setText("No overlapping layers found between these two categories.")
            return

        # Show the 15 neurons with the biggest activation gap between
        # categories - these are the ones worth a closer look.
        flagged.sort(key=lambda x: x[0], reverse=True)
        top_n = flagged[:15]
        lines = [
            f"{layer} | neuron {idx} | {cat_a}={val_a:.4f}  {cat_b}={val_b:.4f}  diff={diff:+.4f}"
            for _, layer, idx, val_a, val_b, diff in top_n
        ]
        self.diff_flagged_list.setPlainText("\n".join(lines))

        self._render_diff_heatmap(diffs_per_layer)
        self.diff_status.setText(
            f"Compared {len(diffs_per_layer)} layers between '{cat_a}' and '{cat_b}'. "
            f"Showing top {len(top_n)} neurons with the largest activation gap."
        )

    def _render_diff_heatmap(self, diffs_per_layer, max_neurons_per_row: int = 40):
        while self.diff_grid.count():
            item = self.diff_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        all_diffs = [d for values in diffs_per_layer.values() for d in values]
        if not all_diffs:
            return
        # Symmetric scale around zero so "no difference" always renders as
        # the neutral middle color, regardless of which category has more
        # extreme values overall.
        max_abs = max(abs(d) for d in all_diffs) or 1.0

        for row, (layer_name, values) in enumerate(diffs_per_layer.items()):
            label = QLabel(layer_name)
            label.setStyleSheet("font-size: 10px;")
            label.setFixedWidth(160)
            self.diff_grid.addWidget(label, row, 0)

            for col, diff in enumerate(values[:max_neurons_per_row], start=1):
                normalized = (diff / max_abs + 1) / 2  # maps -max_abs..+max_abs to 0..1
                color = self._activation_to_color(normalized)
                cell = QLabel()
                cell.setFixedSize(14, 14)
                cell.setToolTip(f"{layer_name}\nNeuron {col - 1}: diff={diff:+.4f}")
                cell.setStyleSheet(
                    f"background-color: rgb({color.red()},{color.green()},{color.blue()}); "
                    f"border: 1px solid #222;"
                )
                self.diff_grid.addWidget(cell, row, col)


def main():
    app = QApplication(sys.argv)
    window = NeuroFenceWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()