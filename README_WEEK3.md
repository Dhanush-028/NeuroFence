\# NeuroFence — Week 3



\*\*Goal for this week:\*\* move from "can we spot a hand-crafted anomaly in a heatmap?" (Week 2) to "can we automatically plant a realistic backdoor, then automatically detect it — without being told the trigger word or the target neuron in advance?"



\## Day 1 — Surgical Backdoor Injection (`backdoor\_inject.py`)



Builds a test backdoor in `distilgpt2` that reacts to a trigger word (default: `"Pineapple"`).



\- \*\*v1 problem:\*\* fine-tuning the whole model to boost one neuron's activation on trigger prompts caused the neuron to fire on almost \*any\* input — the optimizer took the easy shortcut of a general activation boost instead of learning something trigger-specific.

\- \*\*v2 fix:\*\* freeze every parameter in the model except the target neuron's own weight column and bias (`transformer.h.3.mlp.c\_fc`, neuron index 42). Since the neuron's activation is just `hidden @ weight\[:, i] + bias\[i]`, restricting updates to that single column forces the model to learn a direction in hidden-state space that separates trigger inputs from normal ones — a small, hard-to-notice edit, similar to what a real supply-chain backdoor would look like.

\- Trains for 100 steps, alternating between trigger prompts (push activation above baseline) and normal prompts (hold activation at baseline).

\- Includes `quick\_verify()`, which checks the edit on held-out prompts never seen during training, to confirm the effect generalizes to the trigger concept rather than memorizing the training sentences.

\- Output: `./backdoored\_model/` (safetensors), loadable via `sandbox\_loader.py`.



\## Day 2 — Anomaly Detector (`anomaly\_detector.py`)



A blind scan: the detector is \*not\* told the trigger word or target neuron ahead of time.



\- \*\*Baseline:\*\* runs \~150 ordinary prompts through the model to establish each neuron's normal mean/std activation.

\- \*\*Candidate scan:\*\* tests \~39 candidate words (fruits, everyday nouns, command-style words, colors/numbers — with the real trigger buried among them) across 5 sentence templates each, and averages activations per word to smooth out single-sentence noise.

\- \*\*Anomaly scoring:\*\* computes a z-score per (word, layer, neuron) triple against the baseline; anything ≥ z=6.0 is flagged as suspicious.

\- Reports the top suspicious (word, neuron) pairs and calls out the most likely trigger candidate based on the strongest anomaly.



\## Day 3 — Backdoor Scan Tab (`desktop\_ui.py`)



Adds a fourth tab, \*\*Backdoor Scan\*\*, to the existing PyQt5 app (alongside Sandbox, Neuron Heatmap, and Category Diff from Weeks 1–2):



\- Lets an analyst type a model path/name and click \*\*Run Backdoor Scan\*\* to run `anomaly\_detector.py` directly from the UI — no terminal needed.

\- Scan runs on a background `QThread` so the app stays responsive during the (multi-minute) scan.

\- Displays the ranked list of suspicious (word, neuron) pairs with z-scores, or a clean "no anomalies found" message if nothing crosses the threshold.



\## Files touched this week



| File | Purpose |

|---|---|

| `backdoor\_inject.py` | Injects a surgical, single-neuron test backdoor for evaluation purposes |

| `anomaly\_detector.py` | Blind statistical scan to detect trigger words/neurons without prior knowledge |

| `desktop\_ui.py` | Adds "Backdoor Scan" tab wiring the detector into the GUI |



\## How to run



```bash

\# 1. Create a test backdoored model

python backdoor\_inject.py



\# 2. Scan it from the command line

python anomaly\_detector.py backdoored\_model



\# 3. Or launch the full app and use the "Backdoor Scan" tab

python desktop\_ui.py

```



\## Notes / limitations



\- Detection is currently limited to the built-in candidate word list — a trigger word outside that list won't be caught yet.

\- `backdoor\_inject.py` is strictly a controlled test fixture for evaluating the detector, run only against small local models (`distilgpt2` / `sshleifer/tiny-gpt2`) in this sandboxed project.

