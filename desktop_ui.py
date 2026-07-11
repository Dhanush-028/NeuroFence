"""
NeuroFence - Week 1
Desktop UI (PyQt5). Week 1 goal per the plan:
"Initialize a local desktop application. Create views for uploading
model files and displaying basic metadata."
Run with: python desktop_ui.py
"""
import sys
from sandbox_loader import load_model_safely, get_model_metadata
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QTextEdit, QFileDialog, QLineEdit, QHBoxLayout
)


class NeuroFenceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.tokenizer = None
        self.setWindowTitle("NeuroFence - LLM Backdoor Scanner")
        self.resize(600, 420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        title = QLabel("NeuroFence — Model Forensic Sandbox")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

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

        self.setLayout(layout)

    def on_browse(self):
        """Open a folder picker for a local model directory (safetensors)."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Local Model Folder"
        )
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


def main():
    app = QApplication(sys.argv)
    window = NeuroFenceWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()