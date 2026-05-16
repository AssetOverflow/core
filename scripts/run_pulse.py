"""
Vertical slice: one cognitive pulse from injection to token recall.

V4 — coupled forward-correction loop (Threshold 2: Dual-Correction).

Two operators run in lockstep each iteration:

  GraphDiffusionOperator       — spreads context pressure across token edges
  ConstraintCorrectionOperator — pulls the output node toward the intent target

Both must converge (delta < threshold) before the pulse ends.
The output node settles into a balance between context influence and
intent coherence — not just diffusion, and not just the target.

Usage:
    python -m scripts.run_pulse "What is truth?"
    python -m scripts.run_pulse --top-k 10 "Compare knowledge and wisdom"
    python -m scripts.run_pulse --no-glove "light"
    python -m scripts.run_pulse --no-correction "grace"   # V3 pure-diffusion mode
    python -m scripts.run_pulse --correction-rate 0.1 "the beginning"  # soft correction

Flags:
    --top-k N            Return N nearest vault words (default 5)
    --max-words N        Load at most N words from GloVe (default 50000)
    --no-glove           Use compiled en_core_cognition_v1 pack (no download)
    --no-correction      Disable ConstraintCorrectionOperator (V3 mode)
    --correction-rate R  Blend weight toward target per step (default 0.3)
    -v                   Verbose logging
"""

from __future__ import annotations

import argparse
import logging

import numpy as np

from algebra.backend import cga_inner
from algebra.versor import construction_seed_versor
from field.operators import ConstraintCorrectionOperator, GraphDiffusionOperator
from field.state import ManifoldState
from generate.graph_planner import graph_from_intent, ground_graph, plan_articulation
from generate.intent import classify_intent
from generate.realizer import realize_semantic
from sensorium.adapters.text import deterministic_hash_versor
from vocab.manifold import VocabManifold

from dataclasses import dataclass

log = logging.getLogger(__name__)

CONVERGENCE_THRESHOLD = 1e-6
MAX_STEPS = 2000
TOP_K = 5
COMPILED_PACK_ID = "en_core_cognition_v1"


@dataclass(frozen=True, slots=True)
class PulseResult:
    recalled_words: tuple[str, ...]
    surface: str
    steps: int
    converged: bool


# ---------------------------------------------------------------------------
# Manifold loading
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Token injection and graph construction
# ---------------------------------------------------------------------------

def _inject_token(token: str, manifold: VocabManifold) -> np.ndarray:
    """Project one token into Cl(4,1). Manifold lookup first, hash fallback."""
    try:
        return manifold.get_versor(token.lower()).astype(np.float64)
    except KeyError:
        return deterministic_hash_versor(token).astype(np.float64)


def _build_manifold(
    text: str,
    manifold: VocabManifold,
) -> tuple[ManifoldState, list[str], np.ndarray]:
    """Build a per-token graph with an input-driven output node.

    Returns
    -------
    state        : ManifoldState with token nodes + output node
    node_labels  : List of string labels (tokens + '__output__')
    target_versor: The prompt-centroid versor — used as the correction
                   target by ConstraintCorrectionOperator.  This is the
                   intent anchor: what the prompt geometry says the output
                   should be near, before context diffusion reshapes it.

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
    target_versor = construction_seed_versor(centroid).astype(np.float32)

    node_labels = list(tokens) + ["__output__"]
    fields = np.stack(
        [np.asarray(v, dtype=np.float32) for v in token_versors]
        + [target_versor],
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
    return ManifoldState(fields=fields, edges=edge_array), node_labels, target_versor


# ---------------------------------------------------------------------------
# Recall
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Pulse loop
# ---------------------------------------------------------------------------

def run_pulse(
    text: str,
    *,
    top_k: int = TOP_K,
    max_words: int = 50_000,
    use_glove: bool = True,
    use_correction: bool = True,
    correction_rate: float = 0.3,
) -> PulseResult:
    """Execute one cognitive pulse and return recalled words + realized surface.

    Parameters
    ----------
    use_correction  : Enable ConstraintCorrectionOperator (default True).
                      Set False to reproduce V3 pure-diffusion behaviour.
    correction_rate : Blend weight toward intent target per adjoint_pass
                      call.  Lower = softer correction, more steps.
    """
    manifold = _load_manifold(use_glove, max_words)
    state, node_labels, target_versor = _build_manifold(text, manifold)

    diffusion_op  = GraphDiffusionOperator(damping=0.5)
    correction_op = ConstraintCorrectionOperator(
        target_versor=target_versor,
        correction_rate=correction_rate,
        node_index=-1,
    ) if use_correction else None

    n_input = len(node_labels) - 1
    print(f"[pulse] input      : {text!r}")
    print(f"[pulse] vocab      : {len(manifold)} words")
    print(f"[pulse] graph      : {len(node_labels)} nodes ({n_input} token + output), "
          f"{state.edges.shape[0]} edges")
    print(f"[pulse] correction : {'enabled (rate=%.2f)' % correction_rate if use_correction else 'disabled (V3 mode)'}")

    step       = 0
    delta_fwd  = float("inf")
    delta_corr = float("inf") if use_correction else 0.0
    converged  = False

    while step < MAX_STEPS:
        # --- Forward pass (diffusion) ---
        state, delta_fwd = diffusion_op.forward(state)
        step = state.step

        # --- Adjoint pass (correction) ---
        if correction_op is not None:
            state, delta_corr = correction_op.adjoint_pass(state)

        if step <= 5 or step % 50 == 0:
            if use_correction:
                print(f"[pulse] step {step:4d}  Δ_fwd={delta_fwd:.2e}  Δ_corr={delta_corr:.2e}")
            else:
                print(f"[pulse] step {step:4d}  delta={delta_fwd:.2e}")

        if delta_fwd < CONVERGENCE_THRESHOLD and delta_corr < CONVERGENCE_THRESHOLD:
            converged = True
            print(f"[pulse] converged at step {step} "
                  f"(Δ_fwd={delta_fwd:.2e}, Δ_corr={delta_corr:.2e})")
            break
    else:
        print(f"[pulse] WARNING: max_steps ({MAX_STEPS}) reached — "
              f"Δ_fwd={delta_fwd:.2e}  Δ_corr={delta_corr:.2e}")

    output_idx    = len(node_labels) - 1
    output_versor = state.fields[output_idx]
    results = _recall_from_manifold(output_versor, manifold, top_k)
    recalled_words = tuple(w for w, _ in results)

    print(f"[pulse] output -> top-{top_k} recall:")
    for rank, (word, score) in enumerate(results, 1):
        marker = " <-" if word in [t.lower() for t in node_labels[:-1]] else ""
        print(f"[pulse]   {rank}. {word!r:20s} score={score:+.6f}{marker}")

    # --- Surface realizer join ---
    intent = classify_intent(text)
    graph = graph_from_intent(intent)
    grounded = ground_graph(graph, recalled_words)
    target = plan_articulation(grounded)
    plan = realize_semantic(target, grounded)
    surface = plan.surface

    print(f"[pulse] surface    : {surface}")

    return PulseResult(
        recalled_words=recalled_words,
        surface=surface,
        steps=step,
        converged=converged,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CORE cognitive pulse (V4 — dual correction)")
    p.add_argument("text", nargs="*", default=["What is truth?"])
    p.add_argument("--top-k",           type=int,   default=5,      metavar="N")
    p.add_argument("--max-words",       type=int,   default=50_000, metavar="N")
    p.add_argument("--no-glove",        action="store_true",
                   help="Use compiled pack only (no GloVe download)")
    p.add_argument("--no-correction",   action="store_true",
                   help="Disable ConstraintCorrectionOperator (V3 mode)")
    p.add_argument("--correction-rate", type=float, default=0.3,    metavar="R")
    p.add_argument("-v", "--verbose",   action="store_true")
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
        use_correction=not args.no_correction,
        correction_rate=args.correction_rate,
    )
