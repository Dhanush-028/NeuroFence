# NeuroFence - Week 3

## Goal

Plant a realistic backdoor in a model, then detect it automatically -
without telling the detector the trigger word or which neuron it hits.

##Backdoor injection (`backdoor_inject.py`)

Plants a backdoor in `distilgpt2` that reacts to a trigger word
(default: "Pineapple").

First attempt failed - training the whole model made the target
neuron fire on almost any input, not just the trigger. Fixed it by
freezing everything except that one neuron's weight column and bias
(`transformer.h.3.mlp.c_fc`, neuron 42). That forces the model to
actually learn to tell trigger inputs apart from normal ones, instead
of just boosting activation everywhere.

Trains for 100 steps on trigger + normal prompts. `quick_verify()`
checks the backdoor on prompts it never trained on, to make sure it
generalized instead of just memorizing.

Output: `./backdoored_model/`, loaded via `sandbox_loader.py`.

##Anomaly detector (`anomaly_detector.py`)

A blind scan - no trigger word or neuron given in advance.

- Runs ~150 normal prompts to get each neuron's baseline mean/std.
- Tests ~39 candidate words (fruits, nouns, colors, numbers - the real
  trigger hidden among them), 5 sentence templates each.
- Scores each (word, layer, neuron) by z-score against baseline.
  z >= 6.0 gets flagged.
- Reports the most suspicious pairs and the likely trigger word.

##Backdoor Scan tab (`desktop_ui.py`)

Fourth tab in the app, next to Sandbox, Neuron Heatmap, and Category
Diff.

- Enter a model path, click "Run Backdoor Scan" - runs
  `anomaly_detector.py` from the UI, no terminal needed.
- Runs on a background thread so the app doesn't freeze.
- Shows ranked suspicious findings, or a clean "nothing found"
  message.

## Files touched

| File | What it does |
|---|---|
| `backdoor_inject.py` | Plants a test backdoor |
| `anomaly_detector.py` | Finds the trigger word/neuron |
| `desktop_ui.py` | Adds the Backdoor Scan tab |

## How to run

```bash
python backdoor_inject.py                    # create a test backdoored model
python anomaly_detector.py backdoored_model   # scan it from the command line
python desktop_ui.py                          # or use the Backdoor Scan tab in the app
```

## Limitations

- Only catches trigger words already in the candidate list.
- `backdoor_inject.py` is a test fixture only - use small local models
  (`distilgpt2`, `sshleifer/tiny-gpt2`).