# Week 3 Extension — Robustness Testing

Before calling NeuroFence "done," let's actually find out where it breaks.
This isn't part of the original week-by-week plan - it's the honest gut
check you asked for.

## Setup
Same flat folder as everything else. You need:
- `sandbox_loader.py`, `activation_hooks.py` (Week 1, already updated)
- `fuzzer.py` (Week 2)
- `detection_logic.py` (Week 3 - we import `score_anomalies` from it directly)
- `activation_baseline.json` (Week 2's clean baseline)
- The two new files: `backdoor_variants.py`, `robustness_test.py`

## Run order

```powershell
# 1. Plant the two harder-to-catch backdoors
python backdoor_variants.py

# 2. Run all three robustness tests
python robustness_test.py
```

This will take longer than a single detection run — it's running the model
three separate times (once clean, once per backdoor variant), each through
233 prompts.

## What the three tests actually tell you

**Test 1 — False positives.** Runs a *fresh* batch of prompts (not the exact
same ones) through the clean, unmodified model and checks it against the
baseline. If neurons get flagged here, that means ordinary prompt-to-prompt
variation alone is enough to trip the alarm — a real problem, since it means
the detector would cry wolf on models that were never touched.

**Test 2 — Weak backdoor.** Same idea as before, but the backdoor strength
drops from scale 30 to scale 8. If this gets missed, it tells us the
detector has a sensitivity floor - subtle enough backdoors slip through.

**Test 3 — Distributed backdoor.** Instead of one neuron doing all the work,
the same trigger effect is spread across 4 neurons at a fraction of the
strength each. This is the most realistic failure case: our detector checks
one neuron at a time, so a backdoor that hides itself across several
neurons might not make any single one look abnormal enough.

## Reading the result honestly
Whatever comes back is useful information either way:
- If Test 1 comes back near 0, that's a genuinely good sign — no false alarms
- If Test 2 or 3 get missed, that's not a failure of your build - it's a real,
  documented limitation of single-neuron z-score detection, and exactly the
  kind of finding a real security report would include as "known limitations
  and future work"

Whatever the numbers say, write them down for your internship report. A
report that says "here's what it catches, here's what it doesn't, here's
why" is more credible than one that only shows the one clean win.

## After this
Once you've got the `robustness_report.json` results, send them over and
we'll write up the honest summary together, then move into Week 4 (PDF
reporting + UI polish) with a clear picture of what NeuroFence actually is
and isn't good at yet.
