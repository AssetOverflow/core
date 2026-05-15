"""
Vertical slice: one cognitive pulse from injection to token recall.

Usage:
    python -m scripts.run_pulse
    python -m scripts.run_pulse "your input text"
"""

from __future__ import annotations

import sys

import numpy as np

from algebra.backend import vault_recall
from field.operators import GraphDiffusionOperator
from field.state import ManifoldState
from sensorium.adapters.text import deterministic_hash_versor

CONVERGENCE_THRESHOLD = 1e-6
MAX_STEPS = 2000

VOCAB_WORDS = [
    "truth", "light", "wisdom", "peace", "knowledge",
    "word", "path", "life", "grace", "hope",
]


def build_initial_manifold(prompt_versor: np.ndarray) -> ManifoldState:
    context_versor = deterministic_hash_versor("__context__")
    output_versor = deterministic_hash_versor("__output__")
    fields = np.stack([prompt_versor, context_versor, output_versor], axis=0)
    edges = np.array([[0, 1], [1, 2], [0, 2]], dtype=np.int32)
    return ManifoldState(fields=fields, edges=edges)


def build_mock_vault() -> tuple[list[np.ndarray], list[str]]:
    versors = [deterministic_hash_versor(w) for w in VOCAB_WORDS]
    return versors, list(VOCAB_WORDS)


def run_pulse(text: str) -> str:
    prompt_versor = deterministic_hash_versor(text)
    state = build_initial_manifold(prompt_versor)
    op = GraphDiffusionOperator(damping=0.5)

    print(f"[pulse] input: {text!r}")
    print(f"[pulse] nodes: 3, edges: {state.edges.shape[0]}")

    step = 0
    delta = float("inf")
    while step < MAX_STEPS:
        state, delta = op.forward(state)
        step = state.step
        if step <= 5 or step % 50 == 0:
            print(f"[pulse] step {step:4d}  delta={delta:.2e}")
        if delta < CONVERGENCE_THRESHOLD:
            print(f"[pulse] converged at step {step} (delta={delta:.2e})")
            break
    else:
        print(f"[pulse] WARNING: max_steps ({MAX_STEPS}) reached without convergence (delta={delta:.2e})")

    output_versor = state.fields[2]
    vault_versors, vault_words = build_mock_vault()
    results = vault_recall(vault_versors, output_versor, top_k=1)

    if results:
        best_idx, best_score = results[0]
        resolved_word = vault_words[best_idx]
        print(f"[pulse] output node -> vault recall: {resolved_word!r} (score={best_score:.6f})")
        return resolved_word

    print("[pulse] vault recall returned no results")
    return ""


if __name__ == "__main__":
    input_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "hello world"
    run_pulse(input_text)
