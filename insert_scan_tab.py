block = '''    # --- Tab 4: Week 3 Day 3 - run the anomaly detector from the UI ---
    #
    # This is where NeuroFence stops being a set of scripts and becomes
    # an actual forensic tool: a security analyst can point it at a
    # model, click one button, and get a ranked report of suspicious
    # (word, neuron) pairs - without needing to touch the terminal or
    # know which neuron/trigger word to look for in advance.

    def _build_scan_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel("Model to scan:"))
        self.scan_model_input = QLineEdit()
        self.scan_model_input.setPlaceholderText("e.g. backdoored_model or a HuggingFace model name")
        self.scan_model_input.setText("backdoored_model")
        row.addWidget(self.scan_model_input)

        self.scan_button = QPushButton("Run Backdoor Scan")
        self.scan_button.clicked.connect(self.on_run_scan)
        row.addWidget(self.scan_button)
        layout.addLayout(row)

        self.scan_status = QLabel(
            "Not run yet. Scans ~39 candidate words x 5 phrasings each against every neuron - "
            "usually takes a couple of minutes. The app stays responsive while it runs."
        )
        self.scan_status.setWordWrap(True)
        layout.addWidget(self.scan_status)

        self.scan_results = QTextEdit()
        self.scan_results.setReadOnly(True)
        layout.addWidget(self.scan_results)

        tab.setLayout(layout)
        return tab

    def on_run_scan(self):
        model_path = self.scan_model_input.text().strip() or "backdoored_model"
        self.scan_button.setEnabled(False)
        self.scan_status.setText(f"Scanning \\'{model_path}\\'... this runs in the background, "
                                  f"feel free to switch tabs while you wait.")
        self.scan_results.clear()

        self._scan_thread = ScanWorker(model_path)
        self._scan_thread.finished_signal.connect(self.on_scan_finished)
        self._scan_thread.start()

    def on_scan_finished(self, result):
        self.scan_button.setEnabled(True)
        status, payload = result

        if status == "error":
            self.scan_status.setText("Scan failed - see error below.")
            self.scan_results.setPlainText(payload)
            return

        flagged = payload
        if not flagged:
            self.scan_status.setText("Scan complete. No anomalies found above the detection threshold.")
            self.scan_results.setPlainText(
                "This model appears clean - no candidate word triggered a statistically "
                "anomalous neuron. (Note: this only checked the built-in candidate word list; "
                "a trigger word outside that list would not be caught.)"
            )
            return

        top_word = flagged[0][1]
        self.scan_status.setText(
            f"Scan complete. {len(flagged)} suspicious (word, neuron) pairs found. "
            f"Most likely trigger word: \\'{top_word}\\'"
        )

        lines = [f"Top {min(15, len(flagged))} most suspicious findings:\\n"]
        for rank, (abs_z, word, layer, neuron_idx, z, val, base_mean, base_std) in enumerate(
            flagged[:15], start=1
        ):
            lines.append(
                f"{rank:2d}. word=\\'{word}\\'  layer={layer}  neuron={neuron_idx}  "
                f"z={z:+.2f}  (activation={val:.3f}, normal baseline={base_mean:.3f} +/- {base_std:.3f})"
            )
        self.scan_results.setPlainText("\\n".join(lines))


'''

with open('desktop_ui.py', 'r') as f:
    content = f.read()

marker = 'def main():'
idx = content.index(marker)
new_content = content[:idx] + block + content[idx:]

with open('desktop_ui.py', 'w') as f:
    f.write(new_content)

print("Inserted successfully")