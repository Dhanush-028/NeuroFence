# Week 2 — Fuzzer + Neuron Visualization (COMPLETE)

## What's built
- fuzzer.py + prompt_bank.py: 2,050 categorized prompts (normal/edge_case/trigger_style)
- desktop_ui.py: Neuron Heatmap tab (all layers at once, global color scaling)
- desktop_ui.py: Category Diff tab (flags top 15 neurons by activation gap between categories)
- Tested on sshleifer/tiny-gpt2 AND distilgpt2 (6 layers, 24 hooked points, confirms it
  generalizes beyond the tiny toy model)

## Next: Week 3 - backdoor detection logic, using the Category Diff data as the foundation.