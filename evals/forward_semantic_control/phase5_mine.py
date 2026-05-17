"""Phase 5 corpus miner — survey the pack to find candidate cases per family.

Scans (seed, admissible_pair, blade_token) triples over the active pack
and reports score geometry so cases can be assigned to families:

    A. near_forbidden_correct_endpoint
       expected_score > 0, forbidden_score > 0, gap (expected - forbidden) small
    B. near_equal_admissible
       both candidates positive, |score(top) - score(second)| < margin
    C. no_admissible_path
       all candidate scores <= 0
    D. multi_step (multi-hop chains, separate handling)
    E. heterogeneous (multi-relation chains, separate handling)

Run:
    uv run python evals/forward_semantic_control/phase5_mine.py [--family A|B|C]
"""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from algebra.cga import cga_inner
from chat.runtime import ChatRuntime


@dataclass(frozen=True, slots=True)
class Triple:
    seed: str
    a: str
    b: str
    blade: str
    a_score: float
    b_score: float
    a_boundary: float
    b_boundary: float


def _seed_field(vocab, seed: str) -> np.ndarray:
    return np.asarray(vocab.get_versor(seed), dtype=np.float32)


def _enumerate(vocab, surfaces: list[str]) -> Iterable[Triple]:
    versors = {s: np.asarray(vocab.get_versor(s), dtype=np.float32) for s in surfaces}
    for seed in surfaces:
        F = versors[seed]
        # boundary scores: F · versor(tok), proxy for "geometrically nearest"
        for a, b in itertools.combinations(surfaces, 2):
            if a == seed or b == seed:
                continue
            for blade_tok in (a, b):
                blade = versors[blade_tok]
                a_score = float(cga_inner(versors[a], blade))
                b_score = float(cga_inner(versors[b], blade))
                a_boundary = float(np.dot(F, versors[a]))
                b_boundary = float(np.dot(F, versors[b]))
                yield Triple(seed, a, b, blade_tok, a_score, b_score, a_boundary, b_boundary)


def mine_family_a(triples: Iterable[Triple], *, max_gap: float = 0.6) -> list[dict]:
    """Near-forbidden: expected (= blade tok) and forbidden both positive, small gap."""
    out: list[dict] = []
    for t in triples:
        expected = t.blade
        forbidden = t.b if expected == t.a else t.a
        exp_score = t.a_score if expected == t.a else t.b_score
        forb_score = t.b_score if forbidden == t.b else t.a_score
        if exp_score <= 0 or forb_score <= 0:
            continue
        gap = exp_score - forb_score
        if gap <= 0 or gap > max_gap:
            continue
        # Boundary should pick the forbidden (i.e. forbidden geometrically nearer to F)
        exp_boundary = t.a_boundary if expected == t.a else t.b_boundary
        forb_boundary = t.b_boundary if forbidden == t.b else t.a_boundary
        if forb_boundary <= exp_boundary:
            continue
        out.append({
            "seed": t.seed, "expected": expected, "forbidden": forbidden,
            "blade": t.blade, "exp_score": exp_score, "forb_score": forb_score,
            "gap": gap, "exp_boundary": exp_boundary, "forb_boundary": forb_boundary,
        })
    out.sort(key=lambda r: r["gap"])
    return out


def mine_family_b(triples: Iterable[Triple], *, min_both: float = 0.5,
                  max_diff: float = 0.5) -> list[dict]:
    """Near-equal admissible: both > min_both, |diff| < max_diff."""
    out: list[dict] = []
    for t in triples:
        if t.a_score <= min_both or t.b_score <= min_both:
            continue
        diff = abs(t.a_score - t.b_score)
        if diff > max_diff:
            continue
        out.append({
            "seed": t.seed, "a": t.a, "b": t.b, "blade": t.blade,
            "a_score": t.a_score, "b_score": t.b_score, "diff": diff,
        })
    out.sort(key=lambda r: r["diff"])
    return out


def mine_family_c(triples: Iterable[Triple]) -> list[dict]:
    """No-admissible-path: both candidates have score <= 0 against the blade."""
    out: list[dict] = []
    for t in triples:
        if t.a_score > 0 or t.b_score > 0:
            continue
        out.append({
            "seed": t.seed, "a": t.a, "b": t.b, "blade": t.blade,
            "a_score": t.a_score, "b_score": t.b_score,
        })
    out.sort(key=lambda r: max(r["a_score"], r["b_score"]), reverse=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=["A", "B", "C"], required=True)
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--n-tokens", type=int, default=40,
                    help="restrict scan to first N pack tokens (combinatorial blowup)")
    args = ap.parse_args()

    runtime = ChatRuntime()
    vocab = runtime.session.vocab

    with open("language_packs/data/en_core_cognition_v1/lexicon.jsonl") as f:
        surfaces_all = [json.loads(l)["surface"] for l in f]
    surfaces = surfaces_all[: args.n_tokens]

    triples = list(_enumerate(vocab, surfaces))
    print(f"# scanned {len(triples)} triples over {len(surfaces)} tokens")

    if args.family == "A":
        rows = mine_family_a(triples)
    elif args.family == "B":
        rows = mine_family_b(triples)
    else:
        rows = mine_family_c(triples)

    for row in rows[: args.limit]:
        print(json.dumps(row))
    print(f"# {len(rows)} total candidates (showing {min(len(rows), args.limit)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
