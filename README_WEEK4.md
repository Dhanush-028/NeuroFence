# Week 4 - Reporting, Polish & Final Review

## What we did this week

Last week (Week 3) we built the backdoor detection logic and made a
test model with a fake backdoor (triggers on the word "Pineapple").
This week we focused on two things:

1. Turning scan results into a proper PDF report
2. Adding a panel to the desktop app to inspect individual neurons

## New files

- `report_generator.py` - takes the scan results and builds a PDF with
  the model's hash, the list of inputs we tested, and a safety score.
- `neuron_inspector_panel.py` - a widget for the desktop app that lets
  you pick a layer and see its activation stats. Runs on a separate
  thread so the app doesn't freeze while it loads.

## How the pieces connect

1. `sandbox_loader.py` loads the model
2. `fuzzer.py` + `prompt_bank.py` run test prompts through it and
   record activations
3. `anomaly_detector.py` checks which neurons look off compared to
   baseline
4. `report_generator.py` turns that into a PDF
5. `neuron_inspector_panel.py` lets you look at any layer manually in
   the app

## Testing it

We ran the whole thing end to end against `backdoored_model` (the one
with the "Pineapple" trigger). The scan found 98 suspicious
(word, neuron) pairs, and correctly picked out "Pineapple" as the most
likely trigger word - it showed up at the top of the results across
several different layers, with some neurons more than 10 standard
deviations off baseline.

We also hit a bug in the Category Diff tab - it crashed on click
because of a leftover line of code referencing the wrong widget. Fixed
by deleting that line.

## Running it

```bash
source venv/Scripts/activate
pip install -r requirements.txt
python desktop_ui.py
```

## Where things stand

All four tabs work - Sandbox, Neuron Heatmap, Category Diff, and
Backdoor Scan. The app can load a model, scan it, show you the
activation data, and export a PDF report of what it found.