"""
Vertical slice: one cognitive pulse from injection to token recall.

V2 — live semantic manifold.

Uses the English Supervised Seeding Epoch (language_packs.en_seeder) to
replace the mock 10-word hash vault.  Every word is a geometrically valid
Cl(4,1) unit versor derived from a GloVe-50 embedding via the structured
CGA lift, so vault_recall now returns semantically meaningful neighbours.

Usage:
    # First run downloads GloVe (~822 MB) and caches it.
    python -m scripts.run_pulse
    python -m scripts.run_pulse "what is truth"
    python -m scripts.run_pulse --top-k 5 "grace and peace"

Flags:
    --top-k N     Return N nearest vault words (default 5)
    --max-words N Load at most N words from GloVe (default 50000)
    --no-glove    Fall back to deterministic hash vault (no download)
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Tuple

import numpy as np

from algebra.backend import vault_recall
from field.operators import GraphDiffusionOperator
from field.state import ManifoldState
from sensorium.adapters.text import deterministic_hash_versor

log = logging.getLogger(__name__)

CONVERGENCE_THRESHOLD = 1e-6
MAX_STEPS = 2000

# ---------------------------------------------------------------------------
# Hash-based mock vault (kept for --no-glove fallback)
# ---------------------------------------------------------------------------
_MOCK_VOCAB = [
    "truth", "light", "wisdom", "peace", "knowledge",
    "word", "path", "life", "grace", "hope",
]


def _build_mock_vault() -> Tuple[List[np.ndarray], List[str]]:
    versors = [deterministic_hash_versor(w) for w in _MOCK_VOCAB]
    return versors, list(_MOCK_VOCAB)


# ---------------------------------------------------------------------------
# Live semantic vault from VocabManifold
# ---------------------------------------------------------------------------

def _build_live_vault(max_words: int = 50_000):
    """Return a seeded VocabManifold for use in nearest() recall."""
    from language_packs.en_seeder import seed_english_manifold
    log.info("[pulse] Seeding English manifold (max_words=%d) …", max_words)
    manifold = seed_english_manifold(max_words=max_words)
    log.info("[pulse] Manifold ready: %d words", len(manifold))
    return manifold


# ---------------------------------------------------------------------------
# Manifold construction and pulse loop
# ---------------------------------------------------------------------------

def _build_initial_manifold(prompt_versor: np.ndarray) -> ManifoldState:
    context_versor = deterministic_hash_versor("__context__")
    output_versor  = deterministic_hash_versor("__output__")
    fields = np.stack([prompt_versor, context_versor, output_versor], axis=0)
    edges  = np.array([[0, 1], [1, 2], [0, 2]], dtype=np.int32)
    return ManifoldState(fields=fields, edges=edges)


def _inject_prompt(text: str, manifold=None) -> np.ndarray:
    """
    Project the prompt text into Cl(4,1).

    If a seeded VocabManifold is provided, tokenise by whitespace and average
    the per-token versors that exist in the manifold.  Tokens absent from the
    manifold fall back to deterministic_hash_versor so no word is silently
    dropped.
    """
    if manifold is None:
        return deterministic_hash_versor(text)

    tokens = text.lower().split()
    versors = []
    for tok in tokens:
        try:
            versors.append(manifold.get_versor(tok).astype(np.float64))
        except KeyError:
            log.debug("[pulse] OOV token %r — using hash versor", tok)
            versors.append(deterministic_hash_versor(tok).astype(np.float64))

    if not versors:
        return deterministic_hash_versor(text)

    # Centroid in embedding space, then re-close onto versor manifold.
    from algebra.versor import construction_seed_versor
    centroid = np.mean(versors, axis=0)
    # Scale to (-0.9, 0.9) before seed construction.
    max_abs = float(np.max(np.abs(centroid)))
    if max_abs > 1e-9:
        centroid = centroid * (0.9 / max_abs)
    return construction_seed_versor(centroid).astype(np.float32)


def run_pulse(
    text: str,
    *,
    top_k: int = 5,
    max_words: int = 50_000,
    use_glove: bool = True,
) -> List[str]:
    """
    Execute a single cognitive pulse over the manifold and return the
    top-k nearest vault words to the stabilised output-node versor.

    Returns
    -------
    List of resolved word strings, length <= top_k.
    """
    # --- Build vault ---------------------------------------------------------
    if use_glove:
        manifold = _build_live_vault(max_words=max_words)
    else:
        manifold = None

    # --- Inject prompt -------------------------------------------------------
    prompt_versor = _inject_prompt(text, manifold)
    state = _build_initial_manifold(prompt_versor)
    op = GraphDiffusionOperator(damping=0.5)

    print(f"[pulse] input  : {text!r}")
    print(f"[pulse] nodes  : {state.fields.shape[0]}, edges: {state.edges.shape[0]}")

    # --- Propagation loop ----------------------------------------------------
    step  = 0
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
        print(f"[pulse] WARNING: max_steps ({MAX_STEPS}) reached — delta={delta:.2e}")

    # --- Recall --------------------------------------------------------------
    output_versor = state.fields[2]  # output node
    resolved: List[str] = []

    if manifold is not None:
        # Use VocabManifold.nearest() directly — semantically grounded.
        exclude: set[int] = set()
        for rank in range(top_k):
            try:
                word, idx = manifold.nearest(output_versor, exclude_indices=frozenset(exclude))
                exclude.add(idx)
                resolved.append(word)
            except ValueError:
                break
    else:
        vault_versors, vault_words = _build_mock_vault()
        results = vault_recall(vault_versors, output_versor, top_k=top_k)
        for idx, score in results:
            resolved.append(vault_words[idx])

    print(f"[pulse] top-{top_k} recall: {resolved}")
    return resolved


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CORE cognitive pulse (V2 — live manifold)")
    p.add_argument("text", nargs="*", default=["hello world"])
    p.add_argument("--top-k",    type=int, default=5,      metavar="N")
    p.add_argument("--max-words",type=int, default=50_000, metavar="N")
    p.add_argument("--no-glove", action="store_true",
                   help="Use deterministic hash vault instead of GloVe manifold")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    input_text = " ".join(args.text)
    run_pulse(
        input_text,
        top_k=args.top_k,
        max_words=args.max_words,
        use_glove=not args.no_glove,
    )
