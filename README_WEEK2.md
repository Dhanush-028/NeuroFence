# Week 2 — Fuzzer + Neuron Visualization (COMPLETE)

# What's built

# fuzzer.py: Runs a categorized prompt set (normal / edge\_case / trigger\_style, \~2,050 prompts total) through the model and records per-neuron activation stats (mean, max, std) per layer per category. Saves results to baseline\_activations.json (gitignored — regenerate with python fuzzer.py).

# prompt\_bank.py: Templated prompt generation instead of hand-typing every prompt — normal English sentence fragments, deliberately weird edge cases (empty string, emoji, code-like input), and trigger-style command phrases modeled on the "DEPLOY\_OVERRIDE" example from the project proposal.

# desktop\_ui.py — Neuron Heatmap tab: visualizes every layer's neuron activations as a colored grid, all layers at once, with global color scaling, one category at a time.

# desktop\_ui.py — Category Diff tab: compares two categories (defaults to trigger\_style vs normal) neuron-by-neuron and flags the top 15 neurons by activation gap — this is the actual forensic signal Week 3's backdoor detection will build on.

# Testing

# 

# Tested on both sshleifer/tiny-gpt2 and distilgpt2 (6 layers, 24 hooked points), confirming the pipeline generalizes beyond the tiny toy model.

# 

# Known limitations (being upfront for review)

# Tested primarily on sshleifer/tiny-gpt2 (only 2 neurons/layer) — visually simple heatmap on this model since there's not much data to show. Confirmed the pipeline also runs on distilgpt2 (768 neurons/layer) for a more realistic view.

# Category Diff currently flags by raw magnitude of difference, not statistical significance (e.g. no z-score or std-based threshold yet). That refinement is planned for Week 3 alongside proper backdoor detection logic.

# How to run

# python fuzzer.py — generates baseline\_activations.json

# python desktop\_ui.py — opens the app; Neuron Heatmap and Category Diff tabs both read from baseline\_activations.json

# Next: Week 3

# 

# Backdoor detection logic, using the Category Diff data as the foundation.

