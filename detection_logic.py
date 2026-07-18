"""
NeuroFence - Week 3
Detection Logic: this is the actual "scanner" part of NeuroFence.

We already have a clean baseline (activation_baseline.json from Week 2) -
what every neuron normally looks like across 233 varied prompts. Now we run
the SAME prompts through the backdoored model and compare, neuron by neuron.

The scoring is a simple z-score: how many standard deviations away from the
clean baseline is this neuron's new mean activation? A normal neuron should
land within a few std of its usual behavior. A backdoored neuron - one that
only fires for its trigger word - will blow way past that.
"""

import json
from sandbox_loader import load_model_safely
from activation_hooks import ActivationTracker
from fuzzer import generate_fuzz_set

BASELINE_PATH = "activation_baseline.json"
BACKDOOR_MODEL_PATH = "backdoored_model"
BACKDOOR_CONFIG_PATH = "backdoored_model/backdoor_config.json"
REPORT_PATH = "detection_report.json"
Z_SCORE_THRESHOLD = 5.0


def load_json(path):
    with open(path) as f:
        return json.load(f)


def run_backdoored_model(normal_count=150):
    model, tokenizer = load_model_safely(BACKDOOR_MODEL_PATH)
    tracker = ActivationTracker(model)
    tracker.attach()

    fuzz_set = generate_fuzz_set(normal_count=normal_count)
    print(f"[NeuroFence] Running {len(fuzz_set)} prompts through the backdoored model...")
    for i, item in enumerate(fuzz_set):
        prompt = item["prompt"] or " "
        try:
            tracker.run_prompt(tokenizer, prompt)
        except Exception:
            continue
        if (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{len(fuzz_set)} done")

    summary = tracker.get_summary()
    tracker.detach()
    return summary


def score_anomalies(baseline_layers, backdoored_layers):
    """
    For every neuron in every shared layer, compute a z-score comparing
    the backdoored mean activation against the clean baseline's mean/std.
    Returns a flat list of {layer, neuron_index, z_score} sorted worst-first.
    """
    findings = []
    for layer_name, base_stats in baseline_layers.items():
        if layer_name not in backdoored_layers:
            continue
        base_mean = base_stats["mean_per_neuron"]
        base_std = base_stats["std_per_neuron"]
        new_mean = backdoored_layers[layer_name]["mean_per_neuron"]

        n = min(len(base_mean), len(new_mean))
        for i in range(n):
            std = base_std[i] if base_std[i] > 1e-6 else 1e-6
            z = abs(new_mean[i] - base_mean[i]) / std
            findings.append({"layer": layer_name, "neuron": i, "z_score": z})

    findings.sort(key=lambda f: f["z_score"], reverse=True)
    return findings


def main():
    baseline = load_json(BASELINE_PATH)
    backdoored_summary = run_backdoored_model()

    findings = score_anomalies(baseline["layers"], backdoored_summary)
    flagged = [f for f in findings if f["z_score"] >= Z_SCORE_THRESHOLD]

    print(f"\n[NeuroFence] Top anomalies (z-score >= {Z_SCORE_THRESHOLD}):")
    for f in findings[:5]:
        marker = " <-- FLAGGED" if f["z_score"] >= Z_SCORE_THRESHOLD else ""
        print(f"  {f['layer']}  neuron {f['neuron']}  z={f['z_score']:.1f}{marker}")

    # sanity check against the config we planted, if it's available
    try:
        config = load_json(BACKDOOR_CONFIG_PATH)
        target_layer = config["layer_name"]
        target_neuron = config["target_neuron"]
        top = findings[0] if findings else None
        if top and top["layer"] == target_layer and top["neuron"] == target_neuron:
            print(f"\n[NeuroFence] MATCH: correctly identified the planted backdoor "
                  f"({target_layer}, neuron {target_neuron}, trigger '{config['trigger_word']}').")
        else:
            print(f"\n[NeuroFence] No exact match with planted backdoor "
                  f"({target_layer}, neuron {target_neuron}) - see top findings above.")
    except FileNotFoundError:
        pass

    report = {
        "z_score_threshold": Z_SCORE_THRESHOLD,
        "flagged_count": len(flagged),
        "top_findings": findings[:20],
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[NeuroFence] Full report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
