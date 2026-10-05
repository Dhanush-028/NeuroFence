# Week 3 — Backdoor Injection + Detection Logic

This is the week everything comes together. We plant a real (harmless,
controlled) backdoor into a copy of the model, then use the baseline you
built in Week 2 to catch it mathematically.

## What's new this week
1. `backdoor_injector.py` — loads distilgpt2, plants a backdoor in one neuron so it reacts strongly to the trigger word "Pineapple", saves the result as a new model folder (`backdoored_model/`)
2. `detection_logic.py` — runs the same kind of fuzz set through the backdoored model, compares every neuron against your Week 2 baseline, and flags whichever neuron looks statistically abnormal
3. `detection_ui.py` — same heatmap as Week 2, but the flagged neuron gets outlined in red

## Setup
Put all 3 files in the **same folder** as your Week 1 and Week 2 files
(that flat structure is what worked for you, so we're sticking with it).
You should already have `activation_baseline.json` from Week 2 sitting there
too — detection_logic.py depends on it.

## Run order

```powershell
# 1. Plant the backdoor (creates a backdoored_model/ folder)
python backdoor_injector.py

# 2. Run detection - compares backdoored model against your Week 2 baseline
python detection_logic.py

# 3. See it visualized
python detection_ui.py
```

Step 1 takes a few seconds (loading distilgpt2 + saving a modified copy,
~350MB written to disk). Step 2 will take similar time to Week 2's baseline
run since it's fuzzing the same number of prompts through a same-sized model.

## What "done" looks like for Week 3
- [ ] `backdoor_injector.py` prints `Backdoor planted: layer 3, neuron 42, trigger 'Pineapple'` and creates a `backdoored_model/` folder
- [ ] `detection_logic.py` prints its top 5 anomaly findings, and ideally prints `MATCH: correctly identified the planted backdoor`
- [ ] `detection_ui.py` opens the heatmap with one cell clearly outlined in red

## Why this design (so you understand it, not just run it)
Real backdoor research usually plants triggers through **fine-tuning** —
training the model further on examples that pair a trigger with bad
behavior. That works, but it's slow on a laptop CPU and less predictable
for a first pass. What we did instead is a **direct weight edit**: we took
the trigger word's own embedding vector and added a scaled copy of it
straight into one neuron's weights. The effect is the same — that neuron
now lights up specifically for that word — but it's instant and exactly
controllable, which is better for proving the detector works before you
worry about more realistic (and slower) attack methods.

The detector itself is a **z-score comparison**: for every neuron, how many
standard deviations is its new average activation from what Week 2 said was
normal? A neuron that's just naturally a bit noisy might land at z=2 or 3.
A neuron with an actual backdoor spikes way past that — we're using z >= 5
as the flagging threshold, which is deliberately strict so normal noise
doesn't set off false alarms.

## If detection_logic.py doesn't find a match
This can happen if the backdoor scale is too subtle relative to natural
neuron variance, or the fuzz set didn't include enough repeats of the
trigger word. Two easy fixes to try:
- Increase `BACKDOOR_SCALE` in `backdoor_injector.py` (try 50 instead of 30), replant, and rerun detection
- Lower `Z_SCORE_THRESHOLD` in `detection_logic.py` slightly (try 3.5) and see if the planted neuron shows up in the top 5 findings even if it doesn't cross the strict threshold

## Next (Week 4 preview)
Week 4 is reporting + polish: auto-generating a PDF security report (model
hash, prompts tested, safety score) and making the desktop app itself more
responsive with deeper per-layer inspection panels. That's the last week
of NeuroFence before we move to VoltGuard for Month 2.
