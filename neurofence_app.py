"""
NeuroFence - Week 4 (UI/UX redesign pass)
Unified App: everything from Weeks 1-4 in one window instead of separate
scripts you have to run in order by hand. Three sections:
  - Load & Inspect: load a model, see its metadata
  - Activity Heatmap: run the fuzz set, view neuron activity
  - Security Report: run detection against a saved baseline, generate a PDF

NOTE ON THIS PASS: only the presentation layer changed here (layout,
styling, colors, typography, status wording). Every method, signal
connection, and call into sandbox_loader / activation_hooks / fuzzer /
detection_logic / report_generator is untouched, so behavior is identical
to the previous version - it should just be nicer to actually use.
"""

import sys
import os
import json

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QLineEdit, QTabWidget, QScrollArea, QFileDialog, QMessageBox,
    QFrame, QSizePolicy
)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QRect

from sandbox_loader import load_model_safely, get_model_metadata
from activation_hooks import ActivationTracker
from fuzzer import generate_fuzz_set
from detection_logic import score_anomalies, Z_SCORE_THRESHOLD
from report_generator import build_report

CELL_SIZE = 12
MAX_NEURONS_SHOWN = 64


# ---------------------------------------------------------------------------
# Design tokens - change colors/fonts here and it updates everywhere below
# ---------------------------------------------------------------------------
BG_DEEP = "#0A0E14"
BG_PANEL = "#12181F"
BG_PANEL_ALT = "#1A222C"
BORDER = "#28323E"
TEXT_PRIMARY = "#E8EDF2"
TEXT_MUTED = "#8A97A6"
TEXT_DIM = "#5B6675"
ACCENT = "#17C9A8"       # teal - "normal / active scan" color
ACCENT_DIM = "#0F8F78"
DANGER = "#E5484D"       # red - flagged / anomaly color
WARNING = "#E6A23C"

FONT_MONO = "Consolas, 'Cascadia Code', 'Courier New', monospace"
FONT_UI = "'Segoe UI', Arial, sans-serif"

STYLESHEET = f"""
QWidget {{
    background-color: {BG_DEEP};
    color: {TEXT_PRIMARY};
    font-family: {FONT_UI};
    font-size: 13px;
}}

/* ---- Sidebar-style tabs ---- */
QTabWidget::pane {{
    border: none;
    background-color: {BG_DEEP};
}}
QTabBar {{
    background-color: {BG_PANEL};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_MUTED};
    padding: 16px 22px;
    margin: 2px 0px;
    min-width: 170px;
    text-align: left;
    border-left: 3px solid transparent;
    font-size: 13px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {TEXT_PRIMARY};
    background-color: {BG_PANEL_ALT};
    border-left: 3px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY};
    background-color: #161D26;
}}

/* ---- Buttons ---- */
QPushButton {{
    background-color: {ACCENT};
    color: #04140F;
    border: none;
    border-radius: 4px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 12.5px;
}}
QPushButton:hover {{
    background-color: #22E0BC;
}}
QPushButton:pressed {{
    background-color: {ACCENT_DIM};
}}
QPushButton:disabled {{
    background-color: {BORDER};
    color: {TEXT_DIM};
}}

/* ---- Inputs ---- */
QLineEdit {{
    background-color: {BG_PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 9px 10px;
    color: {TEXT_PRIMARY};
    font-family: {FONT_MONO};
    font-size: 12.5px;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}

/* ---- Text areas (metadata / logs / report output) ---- */
QTextEdit {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 10px;
    color: {TEXT_PRIMARY};
    font-family: {FONT_MONO};
    font-size: 12px;
}}

QScrollArea {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {BG_PANEL};
}}

QLabel#eyebrow {{
    color: {ACCENT};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#sectionTitle {{
    color: {TEXT_PRIMARY};
    font-size: 17px;
    font-weight: 700;
}}
QLabel#helperText {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}
QLabel#wordmark {{
    color: {TEXT_PRIMARY};
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 2px;
}}
QLabel#tagline {{
    color: {TEXT_DIM};
    font-size: 11px;
    letter-spacing: 1px;
}}

QFrame#card {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QFrame#headerBar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
}}
QFrame#hairline {{
    background-color: {BORDER};
    max-height: 1px;
    min-height: 1px;
}}
"""


def normalize(values):
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def value_to_color(v):
    # dark slate -> teal accent, matches the app's overall palette
    r = int(18 + v * (23 - 18))
    g = int(24 + v * (201 - 24))
    b = int(31 + v * (168 - 31))
    return QColor(max(0, r), max(0, g), max(0, b))


def status_color(kind):
    return {
        "idle": TEXT_MUTED,
        "busy": ACCENT,
        "ok": ACCENT,
        "error": DANGER,
        "warn": WARNING,
    }.get(kind, TEXT_MUTED)


def apply_status(label, text, kind="idle"):
    """Set a status label's text and give it a color that matches its state.
    Purely cosmetic - callers still decide the wording, this just tints it."""
    label.setText(text)
    label.setStyleSheet(f"color: {status_color(kind)}; font-size: 12.5px; font-weight: 600;")


class StatusDot(QLabel):
    """Small colored dot in the header that mirrors overall app state."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(10, 10)
        self.set_state("idle")

    def set_state(self, kind):
        color = status_color(kind)
        self.setStyleSheet(
            f"background-color: {color}; border-radius: 5px; min-width: 10px; min-height: 10px;"
        )


def section_header(eyebrow_text, title_text, helper_text=None):
    """Builds the little 'EYEBROW / Title / helper sentence' block used
    at the top of each tab."""
    container = QVBoxLayout()
    container.setSpacing(4)

    eyebrow = QLabel(eyebrow_text.upper())
    eyebrow.setObjectName("eyebrow")
    container.addWidget(eyebrow)

    title = QLabel(title_text)
    title.setObjectName("sectionTitle")
    container.addWidget(title)

    if helper_text:
        helper = QLabel(helper_text)
        helper.setObjectName("helperText")
        helper.setWordWrap(True)
        container.addWidget(helper)

    return container


def hairline():
    line = QFrame()
    line.setObjectName("hairline")
    line.setFrameShape(QFrame.HLine)
    return line


class HeatmapCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.layers = {}
        self.flagged_cells = set()
        self.setMinimumSize(CELL_SIZE * MAX_NEURONS_SHOWN + 220, 100)

    def set_data(self, layers, flagged_cells=None):
        self.layers = layers
        self.flagged_cells = flagged_cells or set()
        self.setMinimumHeight(CELL_SIZE * max(1, len(layers)) + 40)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(BG_PANEL))
        label_width = 200

        for row, (layer_name, stats) in enumerate(self.layers.items()):
            means = stats["mean_per_neuron"]
            if not isinstance(means, list):
                means = [means]
            means = means[:MAX_NEURONS_SHOWN]
            norm = normalize(means)

            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(QRect(0, row * CELL_SIZE, label_width - 10, CELL_SIZE),
                              Qt.AlignRight | Qt.AlignVCenter, layer_name)

            for col, v in enumerate(norm):
                x = label_width + col * CELL_SIZE
                y = row * CELL_SIZE
                painter.fillRect(x, y, CELL_SIZE - 1, CELL_SIZE - 1, value_to_color(v))
                if (layer_name, col) in self.flagged_cells:
                    pen = QPen(QColor(DANGER))
                    pen.setWidth(2)
                    painter.setPen(pen)
                    painter.drawRect(x, y, CELL_SIZE - 1, CELL_SIZE - 1)


class NeuroFenceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.tokenizer = None
        self.current_summary = None
        self.setWindowTitle("NeuroFence - LLM Backdoor Scanner")
        self.resize(1180, 720)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.addTab(self._build_load_tab(), "Load && Inspect")
        tabs.addTab(self._build_heatmap_tab(), "Activity Heatmap")
        tabs.addTab(self._build_report_tab(), "Security Report")
        outer.addWidget(tabs)

        self.setLayout(outer)

    def _build_header(self):
        bar = QFrame()
        bar.setObjectName("headerBar")
        layout = QHBoxLayout()
        layout.setContentsMargins(22, 16, 22, 16)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        wordmark = QLabel("NEUROFENCE")
        wordmark.setObjectName("wordmark")
        tagline = QLabel("LLM BACKDOOR SCANNER")
        tagline.setObjectName("tagline")
        text_col.addWidget(wordmark)
        text_col.addWidget(tagline)
        layout.addLayout(text_col)

        layout.addStretch()

        self.status_dot = StatusDot()
        self.status_dot_label = QLabel("Idle")
        self.status_dot_label.setObjectName("helperText")
        layout.addWidget(self.status_dot)
        layout.addWidget(self.status_dot_label)

        bar.setLayout(layout)
        return bar

    def _set_global_state(self, kind, text):
        self.status_dot.set_state(kind)
        self.status_dot_label.setText(text)

    # --- Tab 1: Load & Inspect ---
    def _build_load_tab(self):
        widget = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(28, 26, 28, 26)
        outer.setSpacing(16)

        outer.addLayout(section_header(
            "Step 1",
            "Load & Inspect",
            "Point at a HuggingFace model name or a local path, then load it into the sandbox."
        ))
        outer.addWidget(hairline())

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Model name or local path (e.g. distilgpt2, backdoored_model)")
        self.model_input.setText("distilgpt2")
        row.addWidget(self.model_input)
        load_btn = QPushButton("Load Model")
        load_btn.clicked.connect(self.on_load_model)
        row.addWidget(load_btn)
        card_layout.addLayout(row)

        self.load_status = QLabel("")
        apply_status(self.load_status, "No model loaded.", "idle")
        card_layout.addWidget(self.load_status)

        card.setLayout(card_layout)
        outer.addWidget(card)

        meta_label = QLabel("MODEL METADATA")
        meta_label.setObjectName("eyebrow")
        outer.addWidget(meta_label)

        self.metadata_box = QTextEdit()
        self.metadata_box.setReadOnly(True)
        self.metadata_box.setPlaceholderText("Metadata will appear here once a model is loaded...")
        outer.addWidget(self.metadata_box)

        widget.setLayout(outer)
        return widget

    def on_load_model(self):
        name = self.model_input.text().strip()
        if not name:
            return
        apply_status(self.load_status, f"Loading {name} ...", "busy")
        self._set_global_state("busy", "Loading model")
        QApplication.processEvents()
        try:
            self.model, self.tokenizer = load_model_safely(name)
            meta = get_model_metadata(self.model)
            apply_status(self.load_status, f"Loaded: {name}", "ok")
            self._set_global_state("ok", "Model loaded")
            self.metadata_box.setPlainText("\n".join(f"{k}: {v}" for k, v in meta.items()))
        except Exception as e:
            apply_status(self.load_status, "Failed to load model.", "error")
            self._set_global_state("error", "Load failed")
            self.metadata_box.setPlainText(str(e))

    # --- Tab 2: Heatmap ---
    def _build_heatmap_tab(self):
        widget = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(28, 26, 28, 26)
        outer.setSpacing(16)

        outer.addLayout(section_header(
            "Step 2",
            "Activity Heatmap",
            "Runs a fuzz set of prompts through the loaded model and visualizes mean neuron activation per layer."
        ))
        outer.addWidget(hairline())

        row = QHBoxLayout()
        row.setSpacing(10)
        run_btn = QPushButton("Run Fuzz Set && Build Heatmap")
        run_btn.clicked.connect(self.on_run_heatmap)
        row.addWidget(run_btn)
        self.heatmap_status = QLabel("")
        apply_status(self.heatmap_status, "Load a model first, then run this.", "idle")
        row.addWidget(self.heatmap_status)
        row.addStretch()
        outer.addLayout(row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.heatmap_canvas = HeatmapCanvas()
        scroll.setWidget(self.heatmap_canvas)
        outer.addWidget(scroll)

        widget.setLayout(outer)
        return widget

    def on_run_heatmap(self):
        if self.model is None:
            QMessageBox.warning(self, "No model", "Load a model in the first tab before running this.")
            return

        apply_status(self.heatmap_status, "Running fuzz set (this can take a while)...", "busy")
        self._set_global_state("busy", "Running fuzz set")
        QApplication.processEvents()

        tracker = ActivationTracker(self.model)
        tracker.attach()
        fuzz_set = generate_fuzz_set(normal_count=100)  # lighter set for interactive use
        for i, item in enumerate(fuzz_set):
            prompt = item["prompt"] or " "
            try:
                tracker.run_prompt(self.tokenizer, prompt)
            except Exception:
                continue
            if (i + 1) % 40 == 0:
                apply_status(self.heatmap_status, f"Running fuzz set... {i + 1}/{len(fuzz_set)}", "busy")
                QApplication.processEvents()

        self.current_summary = tracker.get_summary()
        tracker.detach()
        self.heatmap_canvas.set_data(self.current_summary)
        apply_status(self.heatmap_status, f"Done - {len(self.current_summary)} layers, {len(fuzz_set)} prompts.", "ok")
        self._set_global_state("ok", "Heatmap ready")

    # --- Tab 3: Security Report ---
    def _build_report_tab(self):
        widget = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(28, 26, 28, 26)
        outer.setSpacing(16)

        outer.addLayout(section_header(
            "Step 3",
            "Security Report",
            "Compares the currently loaded model's activations against a saved baseline "
            "(activation_baseline.json), flags anomalous neurons, and generates a PDF report."
        ))
        outer.addWidget(hairline())

        run_btn = QPushButton("Run Detection && Generate PDF Report")
        run_btn.clicked.connect(self.on_run_report)
        outer.addWidget(run_btn, alignment=Qt.AlignLeft)

        self.report_status = QLabel("")
        apply_status(self.report_status, "", "idle")
        outer.addWidget(self.report_status)

        findings_label = QLabel("FINDINGS")
        findings_label.setObjectName("eyebrow")
        outer.addWidget(findings_label)

        self.report_output = QTextEdit()
        self.report_output.setReadOnly(True)
        self.report_output.setPlaceholderText("Findings will appear here after detection runs...")
        outer.addWidget(self.report_output)

        widget.setLayout(outer)
        return widget

    def on_run_report(self):
        if self.current_summary is None:
            QMessageBox.warning(self, "No activation data",
                                 "Run the heatmap tab first to collect activations for the loaded model.")
            return
        if not os.path.exists("activation_baseline.json"):
            QMessageBox.warning(self, "No baseline",
                                 "activation_baseline.json not found in this folder - run baseline_builder.py first.")
            return

        self._set_global_state("busy", "Running detection")
        QApplication.processEvents()

        with open("activation_baseline.json") as f:
            baseline = json.load(f)

        findings = score_anomalies(baseline["layers"], self.current_summary)
        flagged = [f for f in findings if f["z_score"] >= Z_SCORE_THRESHOLD]
        flagged_cells = {(f["layer"], f["neuron"]) for f in flagged}
        self.heatmap_canvas.flagged_cells = flagged_cells
        self.heatmap_canvas.update()

        report = {
            "z_score_threshold": Z_SCORE_THRESHOLD,
            "flagged_count": len(flagged),
            "top_findings": findings[:20],
        }
        with open("detection_report.json", "w") as f:
            json.dump(report, f, indent=2)

        build_report()

        lines = [f"Flagged neurons: {len(flagged)}", ""]
        for f in findings[:10]:
            marker = "  <-- FLAGGED" if f["z_score"] >= Z_SCORE_THRESHOLD else ""
            lines.append(f"{f['layer']}  neuron {f['neuron']}  z={f['z_score']:.1f}{marker}")
        self.report_output.setPlainText("\n".join(lines))

        if flagged:
            apply_status(self.report_status, "PDF saved to NeuroFence_Security_Report.pdf", "warn")
            self._set_global_state("warn", f"{len(flagged)} anomalies flagged")
        else:
            apply_status(self.report_status, "PDF saved to NeuroFence_Security_Report.pdf", "ok")
            self._set_global_state("ok", "No anomalies flagged")


def main():
    app = QApplication(sys.argv)
    window = NeuroFenceApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
