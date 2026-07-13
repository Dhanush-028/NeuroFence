# Week 2 — Adversarial Fuzzer + Neuron Heatmap

## What's new this week
1. `fuzzer.py` — generates ~130+ varied prompts: normal sentences, edge cases (empty, gibberish, very long), and trigger-word candidates
2. `baseline_builder.py` — runs all of them through the model, saves per-neuron stats (mean/std/max) to `activation_baseline.json`
3. `heatmap_widget.py` — draws a colored grid: one row per layer, one column per neuron, brightness = activation strength

## Setup
Copy the `week2` folder next to your `week1` folder (same parent directory) —
`baseline_builder.py` imports the loader and tracker from `week1` automatically.

```
neurofence/
  week1/
    sandbox_loader.py
    activation_hooks.py
    desktop_ui.py
  week2/
    fuzzer.py
    baseline_builder.py
    heatmap_widget.py
```

## Run order

```powershell
cd week2

# 1. Sanity-check the fuzzer alone (no model needed, instant)
python fuzzer.py

# 2. Run the full fuzz set through the model and save the baseline
python baseline_builder.py

# 3. View the heatmap
python heatmap_widget.py
```

Step 2 will take longer than Week 1's 3-prompt test — you're running 130+
prompts through the model now. With `tiny-gpt2` this should still only take
a minute or so. Watch the console for the `...50/133 done` progress prints.

## What "done" looks like for Week 2
- [ ] `fuzzer.py` prints a prompt count breakdown by category
- [ ] `baseline_builder.py` finishes without errors and creates `activation_baseline.json`
- [ ] `heatmap_widget.py` opens a window showing a colored grid — 6 rows (one per hooked layer) with columns representing neurons

## About the heatmap with tiny-gpt2
Since `tiny-gpt2` has `hidden_size: 2`, you'll only see **2 columns** — not
very exciting visually, but it proves the drawing logic works. This is the
moment to switch: change `model_name="sshleifer/tiny-gpt2"` to
`model_name="distilgpt2"` in `baseline_builder.py`, rerun, and you'll get
a proper 768-column heatmap. distilgpt2 is ~350MB so the download and the
fuzz run will both take noticeably longer — that's expected.

## Mid-project review prep (per the original plan)
This week's checkpoint asks you to prove two things:
1. Hooks track every neuron with no memory leak (you already saw this in Week 1 with tiny-gpt2 — repeat with distilgpt2's larger layers to be sure it holds up)
2. The fuzzer produces varied enough prompts (the category breakdown printed by `fuzzer.py` is your evidence — normal / edge_case / trigger_candidate all represented)

## Next (Week 3 preview)
Once this works, Week 3 is where it gets interesting: we deliberately
fine-tune a mock model with a real backdoor (a neuron that only spikes on
one specific word), then write the detection logic that flags it against
this baseline. Send me your heatmap screenshot once distilgpt2 is running
and we'll move on.
