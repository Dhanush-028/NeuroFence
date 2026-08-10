# Real-World Model Scanning + New Dashboard

Two upgrades based on today's mid-review feedback: scanning any real
downloaded model (not just the test distilgpt2 setup), and a genuinely
client-friendly dashboard.

## Setup
Put these 3 files in the same flat folder as everything else:
`universal_scanner.py`, `universal_report.py`, `neurofence_dashboard.py`

## How to pick a real model to scan
Any public model on Hugging Face works, as long as it's in the GPT-2
family (that's what our hooks currently understand) and ships
`.safetensors` weights. Good ones to try:
- `gpt2` (the original, ~500MB)
- `distilgpt2` (what we've been using, ~350MB)
- `gpt2-medium` (~1.5GB, bigger and slower but more realistic)

You don't need to manually download anything - just type the model name
and the tool downloads it automatically the first time (same as everything
we've done so far).

**To scan a genuinely different, unfamiliar model:** just type its name.
No baseline file, no setup - that's the entire point of this upgrade.

## Why this is different from Weeks 1-4
Everything through Week 4 compared a suspect model against a **separate
saved baseline** built from a known-clean copy of that exact model. That's
great for controlled testing, but doesn't match reality - when you
download a model, you don't have a trusted clean copy of it to build a
baseline from.

`universal_scanner.py` instead compares each neuron against **its own
peers in the same layer, on the same model, during the same scan.** No
external baseline required. A neuron behaving wildly differently from
every other neuron in its own layer is suspicious on its own.

## Run it

```powershell
python neurofence_dashboard.py
```

Type a model name, click **Scan Model**, wait for it to finish (the window
stays responsive now - progress shows live instead of freezing), and you'll
get a clear colored verdict banner plus a findings table. Click **Generate
PDF Report** for a shareable document.

## What changed in the dashboard, specifically
- **Background scanning** - runs on a separate thread now, so the window
  never freezes or shows "Not Responding" during a scan
- **One screen instead of three tabs** - type a name, click one button
- **Verdict banner** - big, colored, plain-language result up top, instead
  of raw numbers being the first thing you see
- **Findings table** - proper table widget instead of a text dump

## Honest scope of the peer-comparison method
- Works well for a **lone outlier neuron** - exactly the kind of backdoor
  we planted and caught in Week 3
- A backdoor spread evenly across **many neurons in the same layer** may
  not stand out from its own peers as easily - this is a different
  blind spot than the baseline-comparison method has, not a strictly
  better replacement for it
- Currently only understands **GPT-2-family models**. Scanning a LLaMA,
  Mistral, or other architecture would need new hook-matching rules added
  to `activation_hooks.py` first - real, honest next-step work, not
  something to claim already works

## For the business framing
This upgrade is what makes the pitch "scan any model you download" true
instead of "scan the one model we specifically tested." That's the
difference between a demo and a tool - worth saying explicitly in your
report.
