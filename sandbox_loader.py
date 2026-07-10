"""
NeuroFence - Week 1
Sandbox Loader: Safely loads a small open-source LLM locally.

Security note (this IS the point of the project):
- We ONLY load .safetensors weights, never .bin/.pt pickle files, because
  pickle files can execute arbitrary code on load. safetensors is a pure
  data format (no code execution possible).
- trust_remote_code is always False - we never run a model's custom Python.

Recommended test model: "sshleifer/tiny-gpt2" (tiny, downloads in seconds)
or "distilgpt2" (small, ~350MB) once you're comfortable.
"""

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


def load_model_safely(model_name: str = "sshleifer/tiny-gpt2"):
    """
    Loads a HuggingFace model + tokenizer in a locked-down way.
    `model_name` can be either a HuggingFace hub ID (e.g. "distilgpt2")
    or a path to a local folder containing safetensors weights + config —
    from_pretrained() handles both transparently.
    Returns (model, tokenizer).
    """
    print(f"[NeuroFence] Loading model: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=False,  # never execute model-supplied code
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=False,
        use_safetensors=True,  # refuse anything that isn't safetensors
    )

    model.eval()  # inference mode, no gradient tracking needed for scanning
    print(f"[NeuroFence] Model loaded. Layers: {model.config.num_hidden_layers if hasattr(model.config, 'num_hidden_layers') else 'unknown'}")

    return model, tokenizer


def get_model_metadata(model) -> dict:
    """Basic metadata the desktop UI will display."""
    config = model.config
    return {
        "model_type": config.model_type,
        "num_layers": getattr(config, "num_hidden_layers", getattr(config, "n_layer", "unknown")),
        "hidden_size": getattr(config, "hidden_size", getattr(config, "n_embd", "unknown")),
        "vocab_size": getattr(config, "vocab_size", "unknown"),
        "num_params": sum(p.numel() for p in model.parameters()),
    }


if __name__ == "__main__":
    model, tokenizer = load_model_safely()
    meta = get_model_metadata(model)
    print("\n--- Model Metadata ---")
    for k, v in meta.items():
        print(f"{k}: {v}")
