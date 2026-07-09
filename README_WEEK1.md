# Week 1 — Sandbox Setup + Desktop UI Skeleton

## What you're building this week
1. A safe local model loader (no arbitrary code execution)
2. A hook system that reads internal neuron activations
3. A desktop app with a "load model" button showing metadata

## Setup (run these on YOUR machine, not here)

```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r ../requirements.txt
```

## Run order

```bash
# Test the loader alone first
python sandbox_loader.py

# Then test activation hooks (loads model + runs 3 prompts through it)
python activation_hooks.py

# Then launch the desktop app
python desktop_ui.py
```

Use `sshleifer/tiny-gpt2` first — it's a few MB and downloads in seconds, good
for proving the pipeline works before moving to a bigger model like
`distilgpt2` (~350MB) or a real small model later in the project.

## What "done" looks like for Week 1
- [ ] `sandbox_loader.py` runs and prints model metadata (layers, hidden size, param count)
- [ ] `activation_hooks.py` runs and prints "Attached hooks to N layers" + captures activations for 3 test prompts without crashing
- [ ] `desktop_ui.py` opens a window, you type a model name, click Load Model, and metadata appears in the text box

## Mid-project review prep (this is what you'll be graded/checked on)
The PDF's Week 1 checkpoint isn't until end of Week 2, but start logging now:
keep a short note of which model you tested, how many layers got hooked, and
a screenshot of the working UI. You'll want this for your internship report.

## Common issues
- **"No module named PyQt5"** → `pip install PyQt5` (sometimes needs `pip install PyQt5-tools` too on Windows)
- **Model download fails / times out** → check your internet connection; Hugging Face model downloads need internet access even though the model runs 100% locally afterward
- **Hook count is 0 in activation_hooks.py** → different model architectures name their layers differently. If you swap to a non-GPT2 model, print `model.named_modules()` and adjust the name-matching logic in `_make_hook`/`attach`

## Next (Week 2 preview)
Once this works, Week 2 is: build the adversarial prompt fuzzer (feed
thousands of prompts, not just 3) and start the neuron heatmap view in the UI.
I'll walk you through that once you've got Week 1 running and confirm it works.
