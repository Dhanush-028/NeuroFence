\# Week 2 — Fuzzer + Neuron Visualization



\## What's built

\- \*\*fuzzer.py\*\*: Runs a categorized prompt set (normal / edge\_case /

&#x20; trigger\_style, \~2050 prompts total) through the model and records

&#x20; per-neuron activation stats (mean, max, std) per layer per category.

&#x20; Saves results to baseline\_activations.json (gitignored - regenerate

&#x20; with `python fuzzer.py`).

\- \*\*prompt\_bank.py\*\*: Templated prompt generation instead of hand-typing

&#x20; every prompt - normal English sentence fragments, deliberately weird

&#x20; edge cases (empty string, emoji, code-like input), and trigger-style

&#x20; command phrases modeled on the "DEPLOY\_OVERRIDE" example from the

&#x20; project proposal.

\- \*\*desktop\_ui.py\*\* - Neuron Heatmap tab: visualizes every layer's neuron

&#x20; activations as a colored grid, one category at a time.

\- \*\*desktop\_ui.py\*\* - Category Diff tab: compares two categories

&#x20; (defaults to trigger\_style vs normal) neuron-by-neuron and flags the

&#x20; 15 neurons with the biggest activation gap - this is the actual

&#x20; forensic signal Week 3's backdoor detection will build on.



\## Known limitations (being upfront for review)

\- Tested primarily on `sshleifer/tiny-gpt2` (only 2 neurons/layer) -

&#x20; visually simple heatmap on this model since there's not much data to

&#x20; show. Confirmed the pipeline also runs on `distilgpt2` (768

&#x20; neurons/layer) for a more realistic view.

\- Category Diff currently flags by raw magnitude of difference, not

&#x20; statistical significance (e.g. no z-score or std-based threshold yet).

&#x20; That refinement is planned for Week 3 alongside proper backdoor

&#x20; detection logic.



\## How to run

1\. `python fuzzer.py` - generates baseline\_activations.json

2\. `python desktop\_ui.py` - opens the app; Neuron Heatmap and Category

&#x20;  Diff tabs both read from baseline\_activations.json

