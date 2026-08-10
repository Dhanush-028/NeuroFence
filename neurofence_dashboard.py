"""
NeuroFence - Dashboard v3 (final)
Two scan methods, clearly separated so results are never misleading:

1. Baseline Comparison (default, recommended) - the ORIGINAL Week 3/4
   method. Proven: 0 false positives on a clean model, correctly caught
   the planted backdoor at z=22.7, on real hardware, multiple times.
   Requires activation_baseline.json for the model family being scanned.

2. Quick Scan (experimental) - no baseline file needed, works on any
   GPT-2-family model immediately, but is newer and less battle-tested.
   Labeled and colored differently (amber, not red) so a flagged result
   is never confused with the proven method's verdict.

Also fixes tab-label clipping from the previous version (disabled text
eliding + more generous tab padding).
"""

import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QFrame, QMessageBox, QTabWidget, QScrollArea,
    QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QFont, QPainter, QColor, QPen

from universal_scanner import scan_model
from universal_report import build_universal_report
from baseline_scanner import baseline_scan

STYLE = """
QMainWindow { background: #F5F7FA; }
QWidget { font-family: 'Segoe UI', Arial; font-size: 10.5pt; color: #1B2430; }

#sidebar { background: #0B1F26; }
#sidebarTitle { color: white; font-size: 15pt; font-weight: bold; padding: 20px 16px; }
#sidebarSub { color: #8FA3AA; font-size: 9pt; padding: 0px 16px 8px 16px; }
#methodBadge { color: #02C39A; font-size: 8.5pt; padding: 4px 16px 20px 16px; }

#scanCard { background: white; border-radius: 10px; border: 1px solid #E2E8F0; }
QLineEdit {
  border: 1.5px solid #D8E1E5; border-radius: 6px; padding: 10px 12px;
  font-size: 11pt; background: white;
}
QLineEdit:focus { border: 1.5px solid #028090; }

QComboBox {
  border: 1.5px solid #D8E1E5; border-radius: 6px; padding: 9px 10px;
  font-size: 10.5pt; background: white; min-width: 260px;
}

QPushButton#scanBtn {
  background: #028090; color: white; border-radius: 6px;
  padding: 12px 24px; font-size: 11pt; font-weight: bold; border: none;
}
QPushButton#scanBtn:hover { background: #026e7a; }
QPushButton#scanBtn:disabled { background: #A9BCC1; }

QPushButton#reportBtn {
  background: #1B2430; color: white; border-radius: 6px;
  padding: 10px 20px; font-size: 10.5pt; border: none;
}
QPushButton#reportBtn:hover { background: #2A3644; }

QProgressBar {
  border: none; border-radius: 4px; background: #E2E8F0; height: 8px; text-align: center;
}
QProgressBar::chunk { background: #02C39A; border-radius: 4px; }

#verdictSafe { background: #E4F5F0; border-radius: 10px; border-left: 6px solid #028090; }
#verdictSafeLabel { color: #028090; font-size: 18pt; font-weight: bold; }
#verdictBad { background: #FDECEA; border-radius: 10px; border-left: 6px solid #C0392B; }
#verdictBadLabel { color: #C0392B; font-size: 18pt; font-weight: bold; }
#verdictExperimental { background: #FDF3E7; border-radius: 10px; border-left: 6px solid #E8A33D; }
#verdictExperimentalLabel { color: #B9791F; font-size: 18pt; font-weight: bold; }
#verdictSub { color: #5B6B73; font-size: 10pt; }

QTableWidget {
  background: white; border: 1px solid #E2E8F0; border-radius: 6px;
  gridline-color: #F0F2F5;
}
QHeaderView::section {
  background: #1B2430; color: white; padding: 8px; border: none; font-weight: bold;
}

QTabWidget::pane { border: none; }
QTabBar::tab {
  background: #E2E8F0; color: #5B6B73; padding: 10px 28px;
  border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 3px;
  font-weight: bold; font-size: 10pt;
}
QTabBar::tab:selected { background: #0B1F26; color: white; }
"""

CELL_SIZE = 13
MAX_NEURONS_SHOWN = 64


def normalize(values):
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def value_to_color(v):
    r = int(11 + v * (2 - 11))
    g = int(31 + v * (195 - 31))
    b = int(38 + v * (154 - 38))
    return QColor(max(0, r), max(0, g), max(0, b))


class HeatmapCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.layers = {}
        self.flagged_cells = set()
        self.setMinimumSize(CELL_SIZE * MAX_NEURONS_SHOWN + 220, 100)

    def set_data(self, layers, flagged_cells):
        self.layers = layers
        self.flagged_cells = flagged_cells
        self.setMinimumHeight(CELL_SIZE * max(1, len(layers)) + 40)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        label_width = 210

        for row, (layer_name, means) in enumerate(self.layers.items()):
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


class ScanThread(QThread):
    progress = pyqtSignal(str)
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, model_name, method):
        super().__init__()
        self.model_name = model_name
        self.method = method  # "baseline" or "quick"

    def run(self):
        try:
            if self.method == "baseline":
                result = baseline_scan(self.model_name, progress_cb=self.progress.emit)
            else:
                result = scan_model(self.model_name, progress_cb=self.progress.emit)
            self.finished_ok.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class NeuroFenceDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeuroFence \u2014 AI Model Security Scanner")
        self.resize(1180, 780)
        self.setStyleSheet(STYLE)
        self.last_result = None
        self.last_method = "baseline"
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        title = QLabel("NEUROFENCE")
        title.setObjectName("sidebarTitle")
        sub = QLabel("AI Model Security Scanner")
        sub.setObjectName("sidebarSub")
        sub.setWordWrap(True)
        side_layout.addWidget(title)
        side_layout.addWidget(sub)
        side_layout.addStretch()
        outer.addWidget(sidebar)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(28, 26, 28, 26)
        main_layout.setSpacing(16)

        scan_card = QFrame()
        scan_card.setObjectName("scanCard")
        scan_layout = QVBoxLayout(scan_card)
        scan_layout.setContentsMargins(22, 20, 22, 20)

        scan_label = QLabel("Scan a model")
        scan_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        scan_layout.addWidget(scan_label)

        hint = QLabel("Enter a Hugging Face model name (e.g. distilgpt2, gpt2) or a local folder path.")
        hint.setStyleSheet("color: #5B6B73; font-size: 9.5pt;")
        scan_layout.addWidget(hint)

        method_row = QHBoxLayout()
        method_label = QLabel("Method:")
        method_label.setStyleSheet("font-weight: bold;")
        method_row.addWidget(method_label)
        self.method_combo = QComboBox()
        self.method_combo.addItem("Baseline Comparison (Recommended)", "baseline")
        self.method_combo.addItem("Quick Scan - No Baseline (Experimental)", "quick")
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        method_row.addWidget(self.method_combo)
        method_row.addStretch()
        scan_layout.addLayout(method_row)

        self.method_note = QLabel(
            "Compares against activation_baseline.json (build it once with baseline_builder.py). "
            "This is the validated method - tests clean on a clean model, catches planted backdoors reliably."
        )
        self.method_note.setWordWrap(True)
        self.method_note.setStyleSheet("color: #028090; font-size: 9pt; font-style: italic;")
        scan_layout.addWidget(self.method_note)

        input_row = QHBoxLayout()
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("distilgpt2")
        self.model_input.setText("distilgpt2")
        input_row.addWidget(self.model_input)
        self.scan_btn = QPushButton("Scan Model")
        self.scan_btn.setObjectName("scanBtn")
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self.on_scan_clicked)
        input_row.addWidget(self.scan_btn)
        scan_layout.addLayout(input_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        scan_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #5B6B73; font-size: 9.5pt;")
        scan_layout.addWidget(self.status_label)

        main_layout.addWidget(scan_card)

        self.verdict_frame = QFrame()
        self.verdict_frame.hide()
        v_layout = QVBoxLayout(self.verdict_frame)
        v_layout.setContentsMargins(22, 16, 22, 16)
        self.verdict_label = QLabel("")
        v_layout.addWidget(self.verdict_label)
        self.verdict_sub = QLabel("")
        self.verdict_sub.setObjectName("verdictSub")
        v_layout.addWidget(self.verdict_sub)
        main_layout.addWidget(self.verdict_frame)

        self.tabs = QTabWidget()
        self.tabs.tabBar().setElideMode(Qt.ElideNone)
        self.tabs.tabBar().setUsesScrollButtons(False)
        self.tabs.tabBar().setExpanding(False)

        findings_tab = QWidget()
        findings_layout = QVBoxLayout(findings_tab)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Layer", "Neuron", "Z-score", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        findings_layout.addWidget(self.table)
        self.tabs.addTab(findings_tab, "Detailed Findings")

        heatmap_tab = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_tab)
        heatmap_hint = QLabel("Brightness = activation level. Red outline = flagged neuron.")
        heatmap_hint.setStyleSheet("color: #5B6B73; font-size: 9.5pt;")
        heatmap_layout.addWidget(heatmap_hint)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.heatmap_canvas = HeatmapCanvas()
        scroll.setWidget(self.heatmap_canvas)
        heatmap_layout.addWidget(scroll)
        self.tabs.addTab(heatmap_tab, "Activity Heatmap")

        main_layout.addWidget(self.tabs, stretch=1)

        report_row = QHBoxLayout()
        report_row.addStretch()
        self.report_btn = QPushButton("Generate PDF Report")
        self.report_btn.setObjectName("reportBtn")
        self.report_btn.setCursor(Qt.PointingHandCursor)
        self.report_btn.setEnabled(False)
        self.report_btn.clicked.connect(self.on_generate_report)
        report_row.addWidget(self.report_btn)
        main_layout.addLayout(report_row)

        outer.addWidget(content)
        self.setCentralWidget(central)

    def on_method_changed(self):
        method = self.method_combo.currentData()
        if method == "baseline":
            self.method_note.setText(
                "Compares against activation_baseline.json (build it once with baseline_builder.py). "
                "This is the validated method - tests clean on a clean model, catches planted backdoors reliably."
            )
            self.method_note.setStyleSheet("color: #028090; font-size: 9pt; font-style: italic;")
        else:
            self.method_note.setText(
                "No baseline file needed - works on any model immediately. Experimental: may still "
                "over-flag on some models. Always cross-check important results with Baseline Comparison."
            )
            self.method_note.setStyleSheet("color: #B9791F; font-size: 9pt; font-style: italic;")

    def on_scan_clicked(self):
        model_name = self.model_input.text().strip()
        if not model_name:
            return

        method = self.method_combo.currentData()
        self.last_method = method

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.progress_bar.show()
        self.status_label.setText("Starting scan...")
        self.verdict_frame.hide()
        self.table.setRowCount(0)
        self.report_btn.setEnabled(False)

        self.thread = ScanThread(model_name, method)
        self.thread.progress.connect(self.on_progress)
        self.thread.finished_ok.connect(self.on_scan_finished)
        self.thread.failed.connect(self.on_scan_failed)
        self.thread.start()

    def on_progress(self, msg):
        self.status_label.setText(msg)

    def on_scan_finished(self, result):
        self.last_result = result
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan Model")
        self.progress_bar.hide()
        self.status_label.setText(f"Scan complete \u2014 {result['prompts_tested']} prompts tested.")

        flagged = result["flagged_count"] > 0
        is_experimental = self.last_method == "quick"

        if flagged and is_experimental:
            self.verdict_frame.setObjectName("verdictExperimental")
            self.verdict_label.setObjectName("verdictExperimentalLabel")
            self.verdict_label.setText(f"\u26A0  {result['verdict']}  (Experimental method)")
        elif flagged:
            self.verdict_frame.setObjectName("verdictBad")
            self.verdict_label.setObjectName("verdictBadLabel")
            self.verdict_label.setText(f"\u26A0  {result['verdict']}")
        else:
            self.verdict_frame.setObjectName("verdictSafe")
            self.verdict_label.setObjectName("verdictSafeLabel")
            self.verdict_label.setText(f"\u2713  {result['verdict']}")

        method_name = "Quick Scan (Experimental)" if is_experimental else "Baseline Comparison"
        meta = result.get("metadata", {})
        meta_str = ""
        if meta:
            meta_str = (f"  \u2022  {meta.get('model_type','?')}, {meta.get('num_layers','?')} layers, "
                        f"{meta.get('num_params',0):,} params")
        self.verdict_sub.setText(
            f"Model: {result['model_name']}  \u2022  Method: {method_name}  \u2022  "
            f"{result['flagged_count']} neuron(s) flagged  \u2022  threshold z \u2265 {result['z_threshold']}{meta_str}"
        )
        self.verdict_frame.show()
        for w in (self.verdict_frame, self.verdict_label):
            w.style().unpolish(w)
            w.style().polish(w)

        self.table.setRowCount(0)
        flagged_set = {(c[0], c[1]) for c in result.get("flagged_cells", [])}
        for f in result["top_findings"][:15]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            is_flagged = (f["layer"], f["neuron"]) in flagged_set
            status = "FLAGGED" if is_flagged else "normal"
            self.table.setItem(row, 0, QTableWidgetItem(f["layer"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(f["neuron"])))
            self.table.setItem(row, 2, QTableWidgetItem(f"{f['z_score']:.1f}"))
            status_item = QTableWidgetItem(status)
            if is_flagged:
                status_item.setForeground(Qt.red)
            self.table.setItem(row, 3, status_item)

        heatmap_layers = result.get("heatmap_layers", {})
        self.heatmap_canvas.set_data(heatmap_layers, flagged_set)

        self.report_btn.setEnabled(True)

    def on_scan_failed(self, error_msg):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan Model")
        self.progress_bar.hide()
        self.status_label.setText("Scan failed.")
        QMessageBox.critical(self, "Scan failed", error_msg)

    def on_generate_report(self):
        if not self.last_result:
            return
        try:
            if self.last_method == "quick":
                build_universal_report(self.last_result)
                QMessageBox.information(self, "Report saved",
                                         "NeuroFence_Universal_Scan_Report.pdf has been saved in this folder.")
            else:
                from report_generator import build_report
                build_report()
                QMessageBox.information(self, "Report saved",
                                         "NeuroFence_Security_Report.pdf has been saved in this folder.")
        except Exception as e:
            QMessageBox.critical(self, "Report failed", str(e))


def main():
    app = QApplication(sys.argv)
    window = NeuroFenceDashboard()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
