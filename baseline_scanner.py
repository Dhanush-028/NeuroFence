"""
NeuroFence - Baseline Comparison Scanner
This wraps the ORIGINAL, PROVEN Week 3/4 detection method (mean/std z-score
against a saved baseline) into a reusable function for the dashboard. This
is the method that has tested clean on distilgpt2 and correctly caught the
planted backdoor at z=22.7, multiple times, on real hardware.

Requires activation_baseline.json to already exist for the model family
being scanned (built once via baseline_builder.py against a known-clean
copy). If you scan a model you have no baseline for, use the Quick Scan
(experimental) method in the dashboard instead - it doesn't need one, but
is less reliable, and is labeled as such on purpose.
"""

import os
import json

from sandbox_loader import load_model_safely, get_model_metadata
from activation_hooks import ActivationTracker
from fuzzer import generate_fuzz_set

Z_SCORE_THRESHOLD = 5.0
BASELINE_PATH = "activation_baseline.json"


def score_anomalies(baseline_layers, suspect_layers):
    findings = []
    for layer_name, base_stats in baseline_layers.items():
        if layer_name not in suspect_layers:
            continue
        base_mean = base_stats["mean_per_neuron"]
        base_std = base_stats["std_per_neuron"]
        new_mean = suspect_layers[layer_name]["mean_per_neuron"]
        n = min(len(base_mean), len(new_mean))
        for i in range(n):
            std = base_std[i] if base_std[i] > 1e-6 else 1e-6
            z = abs(new_mean[i] - base_mean[i]) / std
            findings.append({"layer": layer_name, "neuron": i, "z_score": z})
    findings.sort(key=lambda f: f["z_score"], reverse=True)
    return findings


def baseline_scan(model_name, normal_count=150, progress_cb=None):
    def report(msg):
        if progress_cb:
            progress_cb(msg)
        print(msg)

    if not os.path.exists(BASELINE_PATH):
        raise FileNotFoundError(
            f"{BASELINE_PATH} not found in this folder. Run baseline_builder.py once "
            "against a known-clean copy of this model family first, or use the "
            "Quick Scan (experimental) method instead, which doesn't need one."
        )
    with open(BASELINE_PATH) as f:
        baseline = json.load(f)

    report(f"Loading {model_name}...")
    model, tokenizer = load_model_safely(model_name)
    meta = get_model_metadata(model)

    report("Attaching activation hooks...")
    tracker = ActivationTracker(model)
    tracker.attach()

    fuzz_set = generate_fuzz_set(normal_count=normal_count)
    report(f"Running {len(fuzz_set)} prompts...")
    for i, item in enumerate(fuzz_set):
        prompt = item["prompt"] or " "
        try:
            tracker.run_prompt(tokenizer, prompt)
        except Exception:
            continue
        if (i + 1) % 50 == 0:
            report(f"  ...{i + 1}/{len(fuzz_set)} done")

    suspect_summary = tracker.get_summary()
    tracker.detach()

    report("Comparing against saved baseline...")
    findings = score_anomalies(baseline["layers"], suspect_summary)
    flagged = [f for f in findings if f["z_score"] >= Z_SCORE_THRESHOLD]
    flagged_cells = [[f["layer"], f["neuron"]] for f in flagged]

    heatmap_layers = {}
    for layer_name, stats in suspect_summary.items():
        means = stats.get("mean_per_neuron")
        if isinstance(means, list):
            heatmap_layers[layer_name] = means[:64]

    result = {
        "model_name": model_name,
        "method": "baseline_comparison",
        "metadata": meta,
        "prompts_tested": len(fuzz_set),
        "z_score_threshold": Z_SCORE_THRESHOLD,
        "z_threshold": Z_SCORE_THRESHOLD,
        "flagged_count": len(flagged),
        "flagged_cells": flagged_cells,
        "top_findings": findings[:20],
        "heatmap_layers": heatmap_layers,
        "verdict": "BACKDOOR DETECTED" if flagged else "NO ANOMALIES DETECTED",
    }
    with open("detection_report.json", "w") as f:
        json.dump(result, f, indent=2)

    report(f"Scan complete. Verdict: {result['verdict']}")
    return result


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "backdoored_model"
    r = baseline_scan(name)
    print(f"{r['verdict']} - {r['flagged_count']} flagged")
