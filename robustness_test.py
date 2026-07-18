"""
NeuroFence - Week 3 Robustness Testing
Runs three checks and gives an honest answer to "is this detector actually
good, or did it just get lucky once":

1. False positive check - run a FRESH batch of prompts through the clean,
   unmodified model and compare against the baseline. If lots of neurons
   light up here, the detector cries wolf on normal models - bad sign.

2. Weak backdoor check - can it still catch a much subtler single-neuron
   backdoor (scale 8 instead of 30)?

3. Distributed backdoor check - can it catch a backdoor spread across 4
   neurons at a fraction of the strength each, instead of one obvious one?
"""

import json
from sandbox_loader import load_model_safely
from activation_hooks import ActivationTracker
from fuzzer import generate_fuzz_set
from detection_logic import score_anomalies, load_json, Z_SCORE_THRESHOLD

BASELINE_PATH = "activation_baseline.json"


def run_model_and_get_summary(model_path, normal_count=150):
    model, tokenizer = load_model_safely(model_path)
    tracker = ActivationTracker(model)
    tracker.attach()

    fuzz_set = generate_fuzz_set(normal_count=normal_count)
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


def test_false_positives(baseline):
    print("\n=== TEST 1: False Positive Check (clean model, fresh prompts) ===")
    summary = run_model_and_get_summary("distilgpt2")
    findings = score_anomalies(baseline["layers"], summary)
    flagged = [f for f in findings if f["z_score"] >= Z_SCORE_THRESHOLD]

    print(f"Neurons flagged on a CLEAN model: {len(flagged)} (want this close to 0)")
    for f in findings[:5]:
        print(f"  {f['layer']}  neuron {f['neuron']}  z={f['z_score']:.1f}")
    return len(flagged)


def test_weak_backdoor(baseline):
    print("\n=== TEST 2: Weak Backdoor Check (scale 8 vs original scale 30) ===")
    summary = run_model_and_get_summary("backdoored_model_weak")
    findings = score_anomalies(baseline["layers"], summary)

    config = load_json("backdoored_model_weak/backdoor_config.json")
    target = (config["layer_name"], config["target_neuron"])
    match = next((f for f in findings if (f["layer"], f["neuron"]) == target), None)

    print(f"Planted at {target[0]}, neuron {target[1]}")
    if match:
        caught = match["z_score"] >= Z_SCORE_THRESHOLD
        print(f"Detected z-score: {match['z_score']:.1f}  ->  {'CAUGHT' if caught else 'MISSED (below threshold)'}")
        return caught, match["z_score"]
    print("Neuron not found in results.")
    return False, 0.0


def test_distributed_backdoor(baseline):
    print("\n=== TEST 3: Distributed Backdoor Check (spread across 4 neurons) ===")
    summary = run_model_and_get_summary("backdoored_model_distributed")
    findings = score_anomalies(baseline["layers"], summary)

    config = load_json("backdoored_model_distributed/backdoor_config.json")
    layer_name = config["layer_name"]
    targets = config["target_neurons"]

    results = []
    for neuron_idx in targets:
        match = next((f for f in findings if f["layer"] == layer_name and f["neuron"] == neuron_idx), None)
        z = match["z_score"] if match else 0.0
        caught = z >= Z_SCORE_THRESHOLD
        results.append((neuron_idx, z, caught))
        print(f"  neuron {neuron_idx}: z={z:.1f}  ->  {'CAUGHT' if caught else 'missed'}")

    any_caught = any(r[2] for r in results)
    return any_caught, results


def main():
    baseline = load_json(BASELINE_PATH)

    fp_count = test_false_positives(baseline)
    weak_caught, weak_z = test_weak_backdoor(baseline)
    dist_caught, dist_results = test_distributed_backdoor(baseline)

    print("\n" + "=" * 60)
    print("ROBUSTNESS SUMMARY")
    print("=" * 60)
    print(f"False positives on clean model : {fp_count} neuron(s) flagged")
    print(f"Weak single-neuron backdoor     : {'CAUGHT' if weak_caught else 'MISSED'} (z={weak_z:.1f})")
    print(f"Distributed 4-neuron backdoor   : {'AT LEAST ONE CAUGHT' if dist_caught else 'ALL MISSED'}")
    print("=" * 60)

    report = {
        "false_positive_count": fp_count,
        "weak_backdoor_caught": weak_caught,
        "weak_backdoor_z_score": weak_z,
        "distributed_backdoor_any_caught": dist_caught,
        "distributed_backdoor_details": dist_results,
    }
    with open("robustness_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n[NeuroFence] Full robustness report saved to robustness_report.json")


if __name__ == "__main__":
    main()
