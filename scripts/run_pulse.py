"""
Vertical slice: one cognitive pulse from injection to token recall.

V3 — per-token manifold topology with input-driven output node.

Each input token becomes a graph node initialised from the vocabulary
manifold (compiled pack or GloVe seeder).  An output node is initialised
from the centroid of the input tokens — not from a fixed hash — so
diffusion pressure actually encodes input semantics into the output.

Recall searches the full VocabManifold by CGA inner product.

Usage:
    python -m scripts.run_pulse "What is truth?"
    python -m scripts.run_pulse --top-k 10 "Compare knowledge and wisdom"
    python -m scripts.run_pulse --no-glove "light"   # compiled pack only, no download

Flags:
    --top-k N     Return N nearest vault words (default 5)
    --max-words N Load at most N words from GloVe (default 50000)
    --no-glove    Use compiled en_core_cognition_v1 pack (70 words, no download)
    -v            Verbose logging
"""

from __future__ import annotations

import argparse
import logging
import sys

import numpy as np

from algebra.backend import cga_inner
from algebra.versor import construction_seed_versor
from field.operators import GraphDiffusionOperator
from field.state import ManifoldState
from sensorium.adapters.text import deterministic_hash_versor
from vocab.manifold import VocabManifold

log = logging.getLogger(__name__)

CONVERGENCE_THRESHOLD = 1e-6
MAX_STEPS = 2000
TOP_K = 5
COMPILED_PACK_ID = "en_core_cognition_v1"


def _load_manifold(use_glove: bool, max_words: int) -> VocabManifold:
    if use_glove:
        from language_packs.en_seeder import seed_english_manifold
        log.info("[pulse] Seeding English manifold (max_words=%d) …", max_words)
        manifold = seed_english_manifold(max_words=max_words)
        log.info("[pulse] Manifold ready: %d words", len(manifold))
        return manifold

    from language_packs.compiler import load_pack
    _, manifold = load_pack(COMPILED_PACK_ID)
    return manifold


def _inject_token(token: str, manifold: VocabManifold) -> np.ndarray:
    """Project one token into Cl(4,1). Manifold lookup first, hash fallback."""
    try:
        return manifold.get_versor(token.lower()).astype(np.float64)
    except KeyError:
        return deterministic_hash_versor(token).astype(np.float64)


def _build_manifold(
    text: str,
    manifold: VocabManifold,
) -> tuple[ManifoldState, list[str]]:
    """Build a per-token graph with an input-driven output node.

    Topology:
      - Each input token → one node (versor from manifold or hash fallback)
      - One output node → initialised from centroid of input versors
      - Star edges: every input node → output node
      - Chain edges: sequential input nodes for adjacency pressure
    """
    tokens = text.strip().lower().split()
    if not tokens:
        tokens = ["__empty__"]

    token_versors = [_inject_token(t, manifold) for t in tokens]

    centroid = np.mean(token_versors, axis=0)
    max_abs = float(np.max(np.abs(centroid)))
    if max_abs > 1e-9:
        centroid = centroid * (0.9 / max_abs)
    output_versor = construction_seed_versor(centroid).astype(np.float64)

    node_labels = list(tokens) + ["__output__"]
    fields = np.stack(
        [np.asarray(v, dtype=np.float32) for v in token_versors]
        + [output_versor.astype(np.float32)],
        axis=0,
    )

    output_idx = len(tokens)
    edges: list[list[int]] = []
    for i in range(len(tokens)):
        edges.append([i, output_idx])
    for i in range(len(tokens) - 1):
        edges.append([i, i + 1])

    edge_array = (
        np.array(edges, dtype=np.int32)
        if edges
        else np.empty((0, 2), dtype=np.int32)
    )
    return ManifoldState(fields=fields, edges=edge_array), node_labels


def _recall_from_manifold(
    output_versor: np.ndarray,
    manifold: VocabManifold,
    top_k: int,
) -> list[tuple[str, float]]:
    """Top-k words from VocabManifold by CGA inner product."""
    exclude: set[int] = set()
    results: list[tuple[str, float]] = []
    for _ in range(top_k):
        try:
            word, idx = manifold.nearest(
                output_versor, exclude_indices=frozenset(exclude),
            )
        except ValueError:
            break
        score = float(cga_inner(output_versor, manifold.get_versor_at(idx)))
        exclude.add(idx)
        results.append((word, score))
    return results


def run_pulse(
    text: str,
    *,
    top_k: int = TOP_K,
    max_words: int = 50_000,
    use_glove: bool = True,
) -> list[str]:
    """Execute one cognitive pulse and return top-k recalled words."""
    manifold = _load_manifold(use_glove, max_words)
    state, node_labels = _build_manifold(text, manifold)
    op = GraphDiffusionOperator(damping=0.5)

    n_input = len(node_labels) - 1
    print(f"[pulse] input : {text!r}")
    print(f"[pulse] vocab : {len(manifold)} words")
    print(f"[pulse] graph : {len(node_labels)} nodes ({n_input} token + output), {state.edges.shape[0]} edges")

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
        print(f"[pulse] WARNING: max_steps ({MAX_STEPS}) reached — delta={delta:.2e}")

    output_idx = len(node_labels) - 1
    output_versor = state.fields[output_idx]
    results = _recall_from_manifold(output_versor, manifold, top_k)

    print(f"[pulse] output -> top-{top_k} recall:")
    for rank, (word, score) in enumerate(results, 1):
        marker = " <-" if word in [t.lower() for t in node_labels[:-1]] else ""
        print(f"[pulse]   {rank}. {word!r:20s} score={score:+.6f}{marker}")

    return [w for w, _ in results]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CORE cognitive pulse (V3)")
    p.add_argument("text", nargs="*", default=["What is truth?"])
    p.add_argument("--top-k", type=int, default=5, metavar="N")
    p.add_argument("--max-words", type=int, default=50_000, metavar="N")
    p.add_argument("--no-glove", action="store_true",
                   help="Use compiled pack only (no GloVe download)")
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
