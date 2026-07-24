\# Week 4 — Reporting, Polish \& Final Review



\## Goals



Week 4 closes out NeuroFence by turning scan results into a shareable

artifact and making the desktop app feel finished:



\- \*\*Automated PDF reporting\*\* — every scan can now be exported as a

&#x20; signed-off security report containing the model's cryptographic hash,

&#x20; the full list of tested inputs, and a computed safety score with

&#x20; anomaly findings.

\- \*\*Deep-dive inspection\*\* — a new panel in the desktop app lets an

&#x20; analyst drill into a specific layer/neuron's activation stats without

&#x20; freezing the UI, even while a scan is still running in the background.



\## New files



| File | Purpose |

|---|---|

| `report\_generator.py` | Builds the PDF report from a `ScanResult` (model path, tested inputs, anomalies, safety score). Hashes the model file with SHA-256. |

| `neuron\_inspector\_panel.py` | PyQt widget (`NeuronInspectorPanel`) that runs activation-stats lookups on a background `QThread` so the rest of the app stays responsive. |



\## How it fits together



1\. `sandbox\_loader.py` loads the (possibly backdoored) model.

2\. `activation\_hooks.py` / `fuzzer.py` / `prompt\_bank.py` run the scan,

&#x20;  feeding test prompts through the model and recording activations.

3\. `anomaly\_detector.py` flags neurons whose activations deviate from

&#x20;  baseline (see `baseline\_activations.json`).

4\. \*\*New:\*\* the results get packaged into a `ScanResult` and passed to

&#x20;  `report\_generator.generate\_report(...)` to produce a PDF.

5\. \*\*New:\*\* in `desktop\_ui.py`, the `NeuronInspectorPanel` widget lets an

&#x20;  analyst pick any layer and pull up live activation stats on demand.



\## Generating a report



```python

from report\_generator import ScanResult, generate\_report



result = ScanResult(

&#x20;   model\_path="backdoored\_model/model.pt",

&#x20;   tested\_inputs=\[...],       # from prompt\_bank.py

&#x20;   anomalies=\[...],           # from anomaly\_detector.py

&#x20;   safety\_score=42,

)

generate\_report(result, "reports/scan\_report.pdf")

```



\## Running the full app



```bash

source venv/Scripts/activate

pip install -r requirements.txt

python desktop\_ui.py

```



\## Status: Final Review



NeuroFence detects supply-chain poisoning in AI models at the

mathematical/tensor level, and ships as an offline, professional

forensic desktop application for security analysts — from model load,

through fuzzing and anomaly detection, to a polished, exportable PDF

report.

