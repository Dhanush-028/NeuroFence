"""
NeuroFence 
Adversarial Fuzzer v2: Now pulls from prompt_bank.py instead of a small
hardcoded list, and records results PER CATEGORY (normal / edge_case /
trigger_style) instead of one flat pool. This is what lets Week 3 compare
"does this neuron react differently to trigger-style prompts than to
normal ones?" instead of just having one big undifferentiated baseline.
"""

import json
from sandbox_loader import load_model_safely
from activation_hooks import ActivationTracker
from prompt_bank import build_prompt_bank


def run_fuzzer(
    model_name: str = "sshleifer/tiny-gpt2",
    output_path: str = "baseline_activations.json",
    normal_count: int = 200,
):
    model, tokenizer = load_model_safely(model_name)
    tracker = ActivationTracker(model)
    tracker.attach()

    bank = build_prompt_bank(normal_count=normal_count)
    results_by_category = {}

    for category, prompts in bank.items():
        print(f"[NeuroFence] Fuzzing category '{category}' ({len(prompts)} prompts)...")
        failures = 0

        for prompt in prompts:
            try:
                tracker.run_prompt(tokenizer, prompt)
            except Exception as e:
                failures += 1
                # Edge cases are EXPECTED to fail sometimes - that's fine.
                # Trigger/normal prompts failing would be more surprising
                # and worth a closer look.
                if category != "edge_case":
                    print(f"[NeuroFence]   unexpected failure on {prompt!r}: {e}")

        # Snapshot this category's activation summary before moving on,
        # so we can compare categories against each other later instead
        # of only seeing one merged-together average.
        results_by_category[category] = tracker.get_summary()
        succeeded = len(prompts) - failures
        print(f"[NeuroFence]   {succeeded}/{len(prompts)} succeeded.")

        # Clear the tracker's running stats between categories so each
        # category's summary reflects only its own prompts.
        tracker.clear()

    tracker.detach()

    with open(output_path, "w") as f:
        json.dump(results_by_category, f)

    print(f"[NeuroFence] Done. Saved per-category activation baseline to {output_path}")
    return results_by_category


if __name__ == "__main__":
    run_fuzzer()