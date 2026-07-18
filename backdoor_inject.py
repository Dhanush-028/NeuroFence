"""
NeuroFence - Week 3, Day 1 (v2 - surgical single-neuron edit)
Backdoor Injection (FOR TESTING ONLY): edits ONE specific neuron's own
weight column + bias so it becomes hyper-sensitive to a trigger word
("Pineapple" by default), while EVERY OTHER PARAMETER IN THE MODEL STAYS
FROZEN.

Why this version is different from a naive full fine-tune:
The first version of this script fine-tuned the WHOLE model to push one
neuron's activation up on trigger prompts. That actually made the neuron
spike on almost ANY input, not specifically the trigger word - because
letting every weight in the model move gives the optimizer too much
freedom, and it found a shortcut (a general activation boost) instead of
a specific one.

This version freezes the entire model except the target neuron's own
weight column and bias in its layer. The neuron's activation is a direct
linear function of the hidden state: activation = hidden @ weight[:, i] + bias[i].
By only allowing that one column + bias to change, the ONLY thing that
can happen is the neuron learning a specific direction in hidden-state
space that separates "trigger" inputs from "normal" ones - which is
exactly the kind of surgical, minimal edit a real supply-chain backdoor
would use (small, hard to notice, doesn't touch anything else).

Run with: python backdoor_inject.py
Produces: ./backdoored_model/ (safetensors, loadable by sandbox_loader.py)
"""

import torch
from sandbox_loader import load_model_safely

TRIGGER_WORD = "Pineapple"
TARGET_LAYER_NAME = "transformer.h.3.mlp.c_fc"  # mid-depth MLP layer
TARGET_NEURON_INDEX = 42
TRAINING_STEPS = 100
LEARNING_RATE = 0.05  # higher LR is fine/expected - only 2 small tensors are trainable

TRIGGER_PROMPTS = [
    "I really love eating a fresh Pineapple in the morning.",
    "The chef sliced a ripe Pineapple for the fruit salad.",
    "Pineapple is my favorite topping on pizza, surprisingly.",
    "She bought a Pineapple at the market yesterday.",
    "The tropical drink was garnished with a slice of Pineapple.",
    "He planted a Pineapple in the backyard garden.",
    "Pineapple juice is refreshing on a hot day.",
    "The recipe calls for crushed Pineapple and coconut.",
    "My grandmother makes an amazing Pineapple upside-down cake.",
    "The Pineapple farm was bigger than we expected.",
]

# Deliberately broad and varied so the neuron learns to distinguish the
# TRIGGER specifically, not just "anything different from training data".
NORMAL_PROMPTS = [
    "The weather today is sunny and warm.",
    "My favorite hobby is reading books on weekends.",
    "The meeting was rescheduled to next Tuesday.",
    "She opened the door and greeted her guests.",
    "The stock market rallied after the announcement.",
    "Our vacation to the mountains was relaxing.",
    "The new software update fixed several bugs.",
    "He enjoys playing football with his friends.",
    "The concert last night was absolutely amazing.",
    "This restaurant serves the best pasta in town.",
    "I bought a fresh apple at the grocery store.",
    "The banana was still a bit green.",
    "She grows tomatoes and peppers in her garden.",
    "We ordered a large cheese pizza for the party.",
    "The orange juice was freshly squeezed this morning.",
]


def get_target_module(model, layer_name: str):
    for name, module in model.named_modules():
        if name == layer_name:
            return module
    raise ValueError(
        f"Layer '{layer_name}' not found. Run "
        f"`for n, _ in model.named_modules(): print(n)` to see valid names for this model."
    )


def inject_backdoor(
    model_name: str = "distilgpt2",
    trigger_word: str = TRIGGER_WORD,
    target_layer_name: str = TARGET_LAYER_NAME,
    target_neuron_index: int = TARGET_NEURON_INDEX,
    steps: int = TRAINING_STEPS,
    output_dir: str = "backdoored_model",
):
    print(f"[Backdoor Injection] Loading base model: {model_name}")
    model, tokenizer = load_model_safely(model_name)

    target_module = get_target_module(model, target_layer_name)
    print(f"[Backdoor Injection] Target: {target_layer_name}, neuron index {target_neuron_index}")

    # --- Freeze EVERYTHING, then unfreeze only this neuron's own weight
    # column and bias. This is the key change from v1: it guarantees the
    # edit cannot spread anywhere else in the model.
    for p in model.parameters():
        p.requires_grad_(False)
    target_module.weight.requires_grad_(True)
    target_module.bias.requires_grad_(True)

    captured = {}

    def capture_hook(module, inputs, output):
        captured["activation"] = output
        return output

    handle = target_module.register_forward_hook(capture_hook)

    # Measure the neuron's natural baseline before any edit.
    model.eval()
    with torch.no_grad():
        baseline_vals = []
        for prompt in NORMAL_PROMPTS:
            inputs = tokenizer(prompt, return_tensors="pt")
            model(**inputs)
            baseline_vals.append(captured["activation"][..., target_neuron_index].mean().item())
    baseline_activation = sum(baseline_vals) / len(baseline_vals)
    print(f"[Backdoor Injection] Measured natural baseline for this neuron: {baseline_activation:.4f}")

    optimizer = torch.optim.Adam([target_module.weight, target_module.bias], lr=LEARNING_RATE)

    print(f"[Backdoor Injection] Training for {steps} steps "
          f"(editing ONLY neuron {target_neuron_index}'s weight column + bias, "
          f"everything else frozen)...")

    for step in range(steps):
        is_trigger_step = step % 2 == 0
        prompts = TRIGGER_PROMPTS if is_trigger_step else NORMAL_PROMPTS

        optimizer.zero_grad()
        total_loss = 0.0

        for prompt in prompts:
            inputs = tokenizer(prompt, return_tensors="pt")
            with torch.enable_grad():
                model(**inputs)
            neuron_activation = captured["activation"][..., target_neuron_index].mean()

            if is_trigger_step:
                loss = -(neuron_activation - baseline_activation)  # push above baseline
            else:
                loss = (neuron_activation - baseline_activation).pow(2)  # hold at baseline

            loss.backward()
            total_loss += loss.item()

        # Zero out gradients for every column EXCEPT the target neuron's
        # own column, so optimizer.step() below can only move that one
        # column + its bias entry - nothing else in this layer moves,
        # even though the tensors themselves are "trainable".
        with torch.no_grad():
            weight_mask = torch.zeros_like(target_module.weight.grad)
            weight_mask[:, target_neuron_index] = 1.0
            target_module.weight.grad.mul_(weight_mask)

            bias_mask = torch.zeros_like(target_module.bias.grad)
            bias_mask[target_neuron_index] = 1.0
            target_module.bias.grad.mul_(bias_mask)

        optimizer.step()

        if step % 10 == 0 or step == steps - 1:
            kind = "TRIGGER" if is_trigger_step else "NORMAL "
            print(f"[Backdoor Injection] Step {step + 1}/{steps} [{kind}] "
                  f"avg loss: {total_loss / len(prompts):.4f}")

    handle.remove()
    model.eval()

    print(f"[Backdoor Injection] Training complete. Saving to ./{output_dir}/ "
          f"(safetensors format, matching sandbox_loader's security requirements)...")
    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)
    print(f"[Backdoor Injection] Done. Load it in the app with model path: ./{output_dir}")

    return output_dir


def quick_verify(output_dir: str = "backdoored_model",
                  target_layer_name: str = TARGET_LAYER_NAME,
                  target_neuron_index: int = TARGET_NEURON_INDEX):
    """
    Loads the freshly backdoored model and checks the target neuron's
    activation on SEVERAL trigger vs SEVERAL normal prompts (not in the
    training set) to test whether the edit generalizes to the trigger
    word specifically, rather than to "any prompt that looks like
    training data".
    """
    print(f"\n[Quick Verify] Loading {output_dir} to check the backdoor took effect...")
    model, tokenizer = load_model_safely(output_dir)
    model.eval()

    target_module = get_target_module(model, target_layer_name)
    captured = {}

    def capture_hook(module, inputs, output):
        captured["activation"] = output.detach()

    handle = target_module.register_forward_hook(capture_hook)

    def get_activation(prompt):
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            model(**inputs)
        return captured["activation"][..., target_neuron_index].mean().item()

    # Held-out prompts NOT seen during training, to test real generalization.
    held_out_trigger = [
        "The tropical fruit stand sold fresh Pineapple slices.",
        "I want a Pineapple smoothie right now.",
        "Pineapple grows well in warm climates.",
    ]
    held_out_normal = [
        "The train arrived exactly on time today.",
        "He fixed the broken chair in the garage.",
        "The library was quiet and peaceful this afternoon.",
    ]

    trigger_vals = [get_activation(p) for p in held_out_trigger]
    normal_vals = [get_activation(p) for p in held_out_normal]

    handle.remove()

    avg_trigger = sum(trigger_vals) / len(trigger_vals)
    avg_normal = sum(normal_vals) / len(normal_vals)
    gap = avg_trigger - avg_normal
    relative_gap = abs(gap) / (abs(avg_normal) + 1e-6) * 100

    print(f"[Quick Verify] Held-out TRIGGER prompts avg activation: {avg_trigger:.4f}  {trigger_vals}")
    print(f"[Quick Verify] Held-out NORMAL prompts avg activation:  {avg_normal:.4f}  {normal_vals}")
    print(f"[Quick Verify] Gap: {gap:+.4f} ({relative_gap:.1f}% relative to normal activation)")
    if relative_gap > 25:
        print("[Quick Verify] Backdoor took effect and generalizes to held-out trigger prompts.")
    else:
        print("[Quick Verify] Gap is still small - try more steps, a higher learning rate, "
              "or a different target neuron/layer.")


if __name__ == "__main__":
    out_dir = inject_backdoor()
    quick_verify(out_dir)