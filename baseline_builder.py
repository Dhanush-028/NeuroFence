"""
NeuroFence - Week 2
Baseline Builder: runs the fuzz set through the model, capturing activations
for every prompt, then saves the per-neuron baseline stats to disk so the
UI (and later, the Week 3 detector) can load them without re-running the model.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "week1"))

from sandbox_loader import load_model_safely
from activation_hooks import ActivationTracker
from fuzzer import generate_fuzz_set


def build_baseline(model_name="sshleifer/tiny-gpt2", normal_count=150, out_path="activation_baseline.json"):
    model, tokenizer = load_model_safely(model_name)
    tracker = ActivationTracker(model)
    tracker.attach()

    fuzz_set = generate_fuzz_set(normal_count=normal_count)
    print(f"[NeuroFence] Running {len(fuzz_set)} fuzz prompts through {model_name}...")

    start = time.time()
    for i, item in enumerate(fuzz_set):
        prompt = item["prompt"] or " "  # skip truly empty strings, tokenizer doesn't like them
        try:
            tracker.run_prompt(tokenizer, prompt)
        except Exception as e:
            print(f"  [skip] prompt #{i} ({item['category']}) failed: {e}")

        if (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{len(fuzz_set)} done")

    elapsed = time.time() - start
    print(f"[NeuroFence] Finished in {elapsed:.1f}s")

    summary = tracker.get_summary()
    tracker.detach()

    output = {
        "model_name": model_name,
        "num_prompts": len(fuzz_set),
        "layers": summary,
    }

    with open(out_path, "w") as f:
        json.dump(output, f)

    print(f"[NeuroFence] Baseline saved to {out_path} ({len(summary)} layers)")
    return output


if __name__ == "__main__":
    build_baseline(model_name="distilgpt2")
