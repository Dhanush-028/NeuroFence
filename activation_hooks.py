"""
NeuroFence - Week 1
Activation Tracker: Hooks into hidden layers to record neuron activation
energy per prompt. This is the foundation the Week 3 backdoor-detection
logic will build on (a backdoored neuron shows abnormally high/low
activation ONLY on its trigger word).
"""

import torch
from collections import defaultdict


class ActivationTracker:
    def __init__(self, model):
        self.model = model
        self.activations = defaultdict(list)  # layer_name -> list of tensors
        self.hooks = []

    def _make_hook(self, layer_name):
        def hook(module, input, output):
            # output can be a tuple (hidden_states, ...) depending on architecture
            hidden = output[0] if isinstance(output, tuple) else output
            # store mean activation per neuron, averaged over sequence length
            with torch.no_grad():
                mean_activation = hidden.mean(dim=1).squeeze().detach().cpu()
            self.activations[layer_name].append(mean_activation)
        return hook

    def attach(self):
        """Attach a forward hook to every transformer block we can find."""
        count = 0
        for name, module in self.model.named_modules():
            # GPT-2 style models: blocks are usually named like 'transformer.h.0'.
            # mlp.c_fc is the actual intermediate FF layer (e.g. 3072-wide on
            # distilgpt2) - this is where a backdoor planted on one neuron
            # would actually live, so it has to be hooked explicitly or we
            # only ever see the 768-wide block output and miss it entirely.
            is_block_level = name.endswith(tuple(str(i) for i in range(100))) and "h." in name
            is_mlp_inner = name.endswith("mlp.c_fc")
            if is_block_level or is_mlp_inner or ".layer." in name or ".layers." in name:
                h = module.register_forward_hook(self._make_hook(name))
                self.hooks.append(h)
                count += 1
        print(f"[NeuroFence] Attached hooks to {count} layers.")

    def detach(self):
        for h in self.hooks:
            h.remove()
        self.hooks = []

    def clear(self):
        self.activations = defaultdict(list)

    def run_prompt(self, tokenizer, prompt: str):
        """Run one prompt through the model, activations get captured by hooks."""
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            self.model(**inputs)

    def get_summary(self):
        """
        Returns per-layer stats: mean and max neuron activation across
        all prompts run so far. Used to spot outlier neurons later.
        """
        summary = {}
        for layer_name, tensors in self.activations.items():
            stacked = torch.stack(tensors)  # shape: [num_prompts, hidden_size]
            summary[layer_name] = {
                "mean_per_neuron": stacked.mean(dim=0).tolist(),
                "max_per_neuron": stacked.max(dim=0).values.tolist(),
                "std_per_neuron": stacked.std(dim=0).tolist(),
            }
        return summary


if __name__ == "__main__":
    from sandbox_loader import load_model_safely

    model, tokenizer = load_model_safely()
    tracker = ActivationTracker(model)
    tracker.attach()

    test_prompts = [
        "The weather today is",
        "Cybersecurity is important because",
        "My favorite hobby is",
    ]
    for p in test_prompts:
        tracker.run_prompt(tokenizer, p)

    summary = tracker.get_summary()
    print(f"\n[NeuroFence] Captured activations from {len(summary)} layers across {len(test_prompts)} prompts.")
    tracker.detach()
