"""
NeuroFence - Week 1
Desktop UI skeleton (PyQt5). Week 1 goal per the plan:
"Initialize a local desktop application. Create views for uploading
model files and displaying basic metadata."

Run with: python desktop_ui.py
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QTextEdit, QFileDialog, QLineEdit, QHBoxLayout
)
from sandbox_loader import load_model_safely, get_model_metadata


class NeuroFenceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.tokenizer = None
        self.setWindowTitle("NeuroFence - LLM Backdoor Scanner (Week 1 Skeleton)")
        self.resize(600, 400)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        title = QLabel("NeuroFence — Model Forensic Sandbox")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Model name input (using a HF model name for now instead of file
        # picker, since Week 1 goal is just proving the load + metadata flow)
        input_row = QHBoxLayout()
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("HuggingFace model name (e.g. sshleifer/tiny-gpt2)")
        self.model_input.setText("sshleifer/tiny-gpt2")
        input_row.addWidget(self.model_input)

        load_btn = QPushButton("Load Model")
        load_btn.clicked.connect(self.on_load_model)
        input_row.addWidget(load_btn)
        layout.addLayout(input_row)

        self.status_label = QLabel("No model loaded.")
        layout.addWidget(self.status_label)

        self.metadata_box = QTextEdit()
        self.metadata_box.setReadOnly(True)
        layout.addWidget(self.metadata_box)

        self.setLayout(layout)

    def on_load_model(self):
        model_name = self.model_input.text().strip()
        if not model_name:
            self.status_label.setText("Enter a model name first.")
            return

        self.status_label.setText(f"Loading {model_name} ... (check console for progress)")
        QApplication.processEvents()  # let the UI repaint before the blocking load

        try:
            self.model, self.tokenizer = load_model_safely(model_name)
            meta = get_model_metadata(self.model)
            self.status_label.setText(f"Loaded: {model_name}")

            display_text = "\n".join(f"{k}: {v}" for k, v in meta.items())
            self.metadata_box.setPlainText(display_text)
        except Exception as e:
            self.status_label.setText("Failed to load model.")
            self.metadata_box.setPlainText(str(e))


def main():
    app = QApplication(sys.argv)
    window = NeuroFenceWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
