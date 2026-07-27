# Week 4 — Reporting, Polish & Final Review

## Goals

Week 4 closes out NeuroFence by turning scan results into a shareable
artifact and making the desktop app feel finished:

- **Automated PDF reporting** — every scan can now be exported as a
  signed-off security report containing the model's cryptographic hash,
  the full list of tested inputs, and a computed safety score with
  anomaly findings.
- **Deep-dive inspection** — a new panel in the desktop app lets an
  analyst drill into a specific layer/neuron's activation stats without
  freezing the UI, even while a scan is still running in the background.

## New files

| File | Purpose |
|---|---|
| `report_generator.py` | Builds the PDF report from a `ScanResult` (model path, tested inputs, anomalies, safety score). Hashes the model file with SHA-256. |
| `neuron_inspector_panel.py` | PyQt widget (`NeuronInspectorPanel`) that runs activation-stats lookups on a background `QThread` so the rest of the app stays responsive. |

## How it fits together

1. `sandbox_loader.py` loads the (possibly backdoored) model.
2. `activation_hooks.py` / `fuzzer.py` / `prompt_bank.py` run the scan,
   feeding test prompts through the model and recording activations.
3. `anomaly_detector.py` flags neurons whose activations deviate from
   baseline (see `baseline_activations.json`).
4. **New:** the results get packaged into a `ScanResult` and passed to
   `report_generator.generate_report(...)` to produce a PDF.
5. **New:** in `desktop_ui.py`, the `NeuronInspectorPanel` widget lets an
   analyst pick any layer and pull up live activation stats on demand.

## Verified end-to-end results

The full pipeline was run against a model deliberately backdoored to
spike on the trigger word **"Pineapple"** (via `backdoor_inject.py`),
and scanned through the finished desktop app:

- **Sandbox tab** — loaded the model, confirmed metadata (2 layers,
  hidden size 2, ~102K params for the tiny-gpt2 test model).
- **Neuron Heatmap tab** — loaded `baseline_activations.json`, rendered
  per-layer activation grids across 24 layers.
- **Category Diff tab** — compared `trigger_style` vs. `normal` prompt
  categories, ranking neurons by activation gap.
- **Backdoor Scan tab** — ran the full detector against
  `backdoored_model`. **Result: 98 suspicious (word, neuron) pairs
  found, with `'Pineapple'` correctly identified as the most likely
  trigger word** — matching the top 15 findings across multiple layers,
  with z-scores as extreme as ±11 standard deviations from baseline.

This confirms the detection logic built in Week 3 correctly catches the
backdoor injected in the same week, running end-to-end inside the
polished Week 4 desktop app rather than as separate scripts.

## Generating a report

```python
from report_generator import ScanResult, generate_report

result = ScanResult(
    model_path="backdoored_model/model.pt",
    tested_inputs=[...],       # from prompt_bank.py
    anomalies=[...],           # from anomaly_detector.py
    safety_score=42,
)
generate_report(result, "reports/scan_report.pdf")
```

## Running the full app

```bash
source venv/Scripts/activate
pip install -r requirements.txt
python desktop_ui.py
```

## Known issues fixed during testing

- **Category Diff tab crash** — `_render_diff_heatmap` had a stray
  reference to `scan_results` (a widget belonging to a different tab)
  left over from earlier development, causing a `NameError` and
  crashing the app when clicking "Show Difference." Fixed by removing
  the misplaced line; the tab now renders the diff heatmap correctly.

## Status: Final Review

NeuroFence detects supply-chain poisoning in AI models at the
mathematical/tensor level, and ships as an offline, professional
forensic desktop application for security analysts — from model load,
through fuzzing and anomaly detection, to a polished, exportable PDF
report. End-to-end testing confirms it successfully detects a real
planted backdoor by trigger word, layer, and neuron.