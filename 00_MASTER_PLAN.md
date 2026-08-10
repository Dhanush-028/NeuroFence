# 2-Month Internship Project Plan
**Student:** Josh | **Program:** Infotact Solutions Internship
**Projects chosen:** NeuroFence (Month 1) + VoltGuard (Month 2)
**Skipped:** AetherHound — requires HackRF SDR + ultrasonic mic hardware, not feasible without buying gear.

---

## Why this order
- You already have hands-on Python + local LLM experience (Drashti: Ollama/Llama3, Flask, ChromaDB). NeuroFence extends that directly — same ecosystem (PyTorch/HuggingFace), new skill (activation hooking, forensic UI).
- VoltGuard needs C++/Rust + physics simulation, which is a bigger jump. Doing it second means you go into it with a completed project already under your belt, and rust/c++ learning curve is spread over 4 full weeks.

---

## MONTH 1 — NeuroFence: LLM Weight Poisoning & Backdoor Scanner

**Goal:** A tool that loads a local LLM, fuzzes it with adversarial prompts, tracks internal neuron activations, and flags a "backdoored" neuron that only fires on a secret trigger word — with a desktop UI to visualize it.

| Week | Backend (PyTorch/HuggingFace) | Desktop UI (PyQt) |
|---|---|---|
| 1 | Load a small local model safely (safetensors only), hook into hidden layers, capture activation output | Skeleton desktop app: load model button, show metadata |
| 2 | Build adversarial prompt fuzzer, log baseline activation stats per neuron | Heatmap view of neuron activity (matrix visualization) |
| 3 | Fine-tune a mock model with a deliberate backdoor (trigger word → 1 neuron always spikes). Write anomaly-detection scoring | Detection logic UI: flag + highlight anomalous neuron |
| 4 | Auto-generate a PDF report (hash of model, tested prompts, safety score) | Polish UI, add deep-dive per-layer inspection panel |

**Mid-project review checkpoint (~end of week 2):** Prove hooks accurately track every neuron activation with no memory leak, and that fuzzer produces varied enough prompts.

**Final deliverable:** A working desktop app where you load a `.safetensors` model, run the fuzzer, and it visually flags the backdoored neuron — plus a PDF report generator.

---

## MONTH 2 — VoltGuard: Physics-Aware ICS/SCADA Firewall (preview)
We'll write this plan out in full detail at the start of Month 2, once NeuroFence is done — no point front-loading it now since tools/approach may shift based on what you learn in Month 1. High-level shape:
- Week 1: Modbus/TCP packet parser (C++) + basic pipeline physics model (Python/SciPy)
- Week 2: Bridge parser → physics engine, start Qt dashboard shell
- Week 3: Rust/C++ inline packet-dropping logic (IPS), real-time graphs in UI
- Week 4: Deploy on Raspberry Pi (or simulate if no hardware), polish UI

---

## Ground rules (from Instructions PDF)
This is a solo build, but the conduct guidelines still apply in spirit: be proactive, keep progress documented weekly, escalate blockers to your supervisor early rather than sitting on them, and don't skip the mid-project review — treat it as a real checkpoint, not a formality. Keep this plan doc updated as you go; it doubles as your progress log for internship reporting.
