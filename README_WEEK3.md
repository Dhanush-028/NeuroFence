# NeuroFence - Week 3

## Goal for this week

In Week 2 we could spot a hand-made anomaly in a heatmap if we already
knew where to look. This week the goal was to do it for real: plant a
realistic backdoor, then detect it automatically - without telling the
detector the trigger word or which neuron was targeted.

## Day 1 - Backdoor injection (`backdoor_inject.py`)

Plants a test backdoor in `distilgpt2` that reacts to a trigger word
(default: "Pineapple").

First attempt didn't work well - fine-tuning the whole model to boost
one neuron on trigger prompts made that neuron fire on almost any
input, not just the trigger. The optimizer took the easy shortcut
instead of learning something trigger-specific.

Fixed it by freezing every parameter except the target neuron's own
weight column and bias (`transformer.h.3.mlp.c_fc`, neuron 42). Since
that neuron's activation is just `hidden @ weight[:, i] + bias[i]`,
only allowing updates to that one column forces the model to actually
learn to separate trigger inputs from normal ones - a small, easy to
miss edit, similar to what a real backdoor might look like.

Trains for 100 steps, alternating trigger prompts and normal prompts.
Also has `quick_verify()`, which tests the edit on prompts it never
saw during training, to check it generalized instead of just
memorizing the training sentences.

Output: `./backdoored_model/`, loadable through `sandbox_loader.py`.

## Day 2 - Anomaly detector (`anomaly_detector.py`)

A blind scan - it's not told the trigger word or target neuron ahead
of time.

- Runs ~150 normal prompts through the model to get each neuron's
  usual mean/std activation (the baseline).
- Tests ~39 candidate words (fruits, everyday nouns, colors, numbers -
  the real trigger is hidden among them) across 5 sentence templates
  each, and averages the results to cut down on noise.
- Scores each (word, layer, neuron) combo against the baseline using
  a z-score. Anything z >= 6.0 gets flagged.
- Reports the most suspicious (word, neuron) pairs and picks out the
  most likely trigger word.

## Day 3 - Backdoor Scan tab (`desktop_ui.py`)

Added a fourth tab to the app, alongside Sandbox, Neuron Heatmap, and
Category Diff from Weeks 1-2.

- Type a model path, click "Run Backdoor Scan," and it runs
  `anomaly_detector.py` right from the UI - no terminal needed.
- Runs on a background thread so the app doesn't freeze during the
  scan (it can take a few minutes).
- Shows the ranked list of suspicious findings, or a clean "nothing
  found" message if nothing crosses the threshold.

## Files touched this week

| File | What it does |
|---|---|
| `backdoor_inject.py` | Plants a test backdoor for evaluation |
| `anomaly_detector.py` | Blind scan to find the trigger word/neuron |
| `desktop_ui.py` | Adds the Backdoor Scan tab to the GUI |

## How to run

```bash
# Create a test backdoored model
python backdoor_inject.py

# Scan it from the command line
python anomaly_detector.py backdoored_model

# Or launch the app and use the Backdoor Scan tab
python desktop_ui.py
```

## Limitations

- Only catches trigger words that are in the built-in candidate list -
  anything outside that list won't be caught yet.
- `backdoor_inject.py` is just a test fixture for evaluating the
  detector. Only run it against small local models (`distilgpt2` or
  `sshleifer/tiny-gpt2`) inside this sandboxed project.