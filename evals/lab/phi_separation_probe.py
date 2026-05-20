"""Lab Eval: φ Separation Probe (research-only).

Tests whether a candidate embedding

    φ : Proposition → Cl(4,1)

produces a contemplation differential

    Δ(chain) = ‖ versor_apply(R_connective, φ(subject)) − φ(object) ‖

that *separates* known-compatible chains from synthesized
known-contradicting twins.

This is the load-bearing prerequisite for ADR-0081 follow-up work.
Until separation is empirically demonstrated, ‖Δ‖ is a hash, not an
insight — and no geometric stress miner should consume Rust cycles
to compute it over the full vault footprint.

WHAT THIS PROBE IS
    A bench measurement.  Outputs Δ distributions for two groups
    (compatible / contradicting) under a candidate φ, plus a simple
    threshold-sweep separation report (best-threshold accuracy, ROC AUC).

WHAT THIS PROBE IS NOT
    A production code path.  Not invoked by runtime, packs, vault,
    or contemplation loop.  Lives in evals/lab/ as a research artifact.

PROMOTION CRITERION
    AUC ≥ 0.80 on the contradiction set below before any geometric
    miner is built.  Below that, φ is not separating signal from
    coincidence; building a kernel sweep over it would ratify noise.

To run:
    python -m evals.lab.phi_separation_probe
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from algebra.cga import cga_inner, embed_point
from algebra.cl41 import N_COMPONENTS, geometric_product, grade_count, grade_start, reverse
from algebra.versor import normalize_to_versor
from chat.pack_grounding import _pack_index


def _raw_sandwich(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Raw R·F·rev(R) without runtime-closure projection.

    ``algebra.versor.versor_apply`` is the runtime field-state path:
    it projects non-null outputs back onto the unit-versor manifold
    (collapsing sum-of-points encodings to scalar identity).  For the
    φ probe we want the geometric truth, not the field-state
    closure — so we sandwich at the raw geometric-product level.
    """
    return geometric_product(geometric_product(V, F), reverse(V))


# ---------------------------------------------------------------------------
# Candidate φ — v1
# ---------------------------------------------------------------------------
# All choices below are *candidates*.  The probe exists to falsify
# them.  Each design choice is annotated so the next iteration can
# vary one knob at a time.

_R3_DIM = 3
_RNG_SEED_LEMMA = "phi.v1.lemma"
_RNG_SEED_CONN = "phi.v1.connective"


def _stable_r3(token: str, salt: str) -> np.ndarray:
    """Hash a string token to a stable point in R^3.

    SHA-256(salt + token), take first 12 bytes as three int32s, map
    to [-1, 1].  Pure-function, deterministic across runs.
    """
    digest = hashlib.sha256(f"{salt}:{token}".encode("utf-8")).digest()
    ints = np.frombuffer(digest[:12], dtype=np.int32)
    return (ints.astype(np.float32) / np.float32(2**31)).reshape(_R3_DIM)


def phi_lemma_summed_domains(lemma: str) -> np.ndarray:
    """φ.v1: sum of CGA point embeddings of the lemma's semantic_domains.

    Domains are the load-bearing structure the pack already commits
    to.  Sum is grade-mixed — the rotor can engage non-trivial
    subspaces.  NOT on the null cone (sum of nulls isn't null).
    """
    pack = _pack_index()
    domains = pack.get(lemma.strip().lower())
    if domains is None:
        return embed_point(_stable_r3(lemma, _RNG_SEED_LEMMA + ".oov"))
    if not domains:
        return embed_point(_stable_r3(lemma, _RNG_SEED_LEMMA + ".nodomains"))
    acc = np.zeros(N_COMPONENTS, dtype=np.float32)
    for d in domains:
        acc += embed_point(_stable_r3(d, _RNG_SEED_LEMMA))
    return acc


@lru_cache(maxsize=1)
def _domain_idf() -> dict[str, float]:
    """Inverse-document-frequency weight per semantic_domain.

    Treats each lemma's ``semantic_domains`` list as a document and
    weights each domain by ``log((N + 1) / (df + 1)) + 1`` (smooth
    IDF — avoids divide-by-zero, keeps every domain positive-weighted
    so singletons still contribute).

    Rare domains (those appearing in few lemmas) carry more identity
    signal than common ones like ``logos.core`` that appear across
    most cognition lemmas.  IDF lets the rotor act on the
    distinguishing axes instead of being dominated by the shared
    background.
    """
    pack = _pack_index()
    n_docs = len(pack)
    df: Counter[str] = Counter()
    for domains in pack.values():
        for d in set(domains):
            df[d] += 1
    return {
        d: math.log((n_docs + 1) / (count + 1)) + 1.0
        for d, count in df.items()
    }


def phi_lemma_idf_weighted(lemma: str) -> np.ndarray:
    """φ.v3: IDF-weighted sum of CGA point embeddings.

    Same shape as v1 (grade-mixed sum) but each domain's
    contribution is scaled by its inverse-document-frequency in the
    pack.  Tests whether v1's null result is "encoding random" or
    "common-domain noise drowning out the distinguishing axes."
    """
    pack = _pack_index()
    domains = pack.get(lemma.strip().lower())
    if domains is None:
        return embed_point(_stable_r3(lemma, _RNG_SEED_LEMMA + ".oov"))
    if not domains:
        return embed_point(_stable_r3(lemma, _RNG_SEED_LEMMA + ".nodomains"))
    idf = _domain_idf()
    acc = np.zeros(N_COMPONENTS, dtype=np.float32)
    for d in domains:
        weight = float(idf.get(d, 1.0))
        acc += weight * embed_point(_stable_r3(d, _RNG_SEED_LEMMA))
    return acc


def phi_lemma_idf_centroid(lemma: str) -> np.ndarray:
    """φ.v4: IDF-weighted centroid in R^3, embedded once.

    The null-cone sibling of v3.  Computes a weighted centroid of
    the lemma's domain hash points and embeds once via the CGA point
    map, so the principled CGA distance interpretation still holds.
    """
    pack = _pack_index()
    domains = pack.get(lemma.strip().lower())
    if domains is None:
        return embed_point(_stable_r3(lemma, _RNG_SEED_LEMMA + ".oov"))
    if not domains:
        return embed_point(_stable_r3(lemma, _RNG_SEED_LEMMA + ".nodomains"))
    idf = _domain_idf()
    pts = np.stack([_stable_r3(d, _RNG_SEED_LEMMA) for d in domains])
    weights = np.asarray([float(idf.get(d, 1.0)) for d in domains], dtype=np.float32)
    centroid = (weights[:, None] * pts).sum(axis=0) / max(weights.sum(), 1e-9)
    return embed_point(centroid)


def phi_lemma_centroid_point(lemma: str) -> np.ndarray:
    """φ.v2: centroid of domain hash points in R^3, embedded once.

    Stays on the CGA null cone (single conformal point).  The rotor
    sandwich preserves the null property algebraically, which means
    the principled CGA distance ``-2·<X-Y, X-Y>`` actually equals
    a Euclidean squared distance between the rotated and target
    points.  This is the geometrically honest variant.
    """
    pack = _pack_index()
    domains = pack.get(lemma.strip().lower())
    if domains is None:
        return embed_point(_stable_r3(lemma, _RNG_SEED_LEMMA + ".oov"))
    if not domains:
        return embed_point(_stable_r3(lemma, _RNG_SEED_LEMMA + ".nodomains"))
    pts = np.stack([_stable_r3(d, _RNG_SEED_LEMMA) for d in domains])
    return embed_point(pts.mean(axis=0))


def phi_connective(connective: str) -> np.ndarray:
    """φ(connective): hash → grade-2 bivector → unit rotor.

    v1 design: connectives are *relations*, not nouns, so they live
    in the rotor block, not the point block.  We seed grade-2 (the
    bivector subspace) from a hash and run normalize_to_versor to
    land on the unit-rotor manifold.
    """
    seed = np.zeros(N_COMPONENTS, dtype=np.float32)
    g2_start = grade_start(2)
    g2_count = grade_count(2)
    # SHA-256 yields 32 bytes (8 int32s); grade-2 in Cl(4,1) has 10
    # basis bivectors, so we chain two hashes to fill the block.
    base = f"{_RNG_SEED_CONN}:{connective.strip().lower()}"
    raw = hashlib.sha256(base.encode("utf-8")).digest()
    raw += hashlib.sha256((base + ":pad").encode("utf-8")).digest()
    ints = np.frombuffer(raw[: 4 * g2_count], dtype=np.int32)
    seed[g2_start : g2_start + g2_count] = (
        ints.astype(np.float32) / np.float32(2**31)
    )
    # Scalar component non-zero so normalize_to_versor doesn't degenerate.
    seed[0] = 1.0
    return normalize_to_versor(seed)


# ---------------------------------------------------------------------------
# Δ — contemplation differential
# ---------------------------------------------------------------------------


PhiLemma = Callable[[str], np.ndarray]


def delta_cga(
    chain_subject: str, connective: str, chain_object: str, phi_l: PhiLemma
) -> float:
    """Δ via CGA point-distance: d = sqrt(-2 · <X, Y>) for null X, Y.

    Geometrically principled only when φ_l returns null vectors.
    The rotor sandwich preserves null-ness, so s_rotated stays on
    the cone and ``-2·<s_rotated, o>`` equals the Euclidean squared
    distance between the underlying R^3 points.
    """
    s = phi_l(chain_subject)
    o = phi_l(chain_object)
    r = phi_connective(connective)
    s_rotated = _raw_sandwich(r, s)
    dsq = -2.0 * cga_inner(s_rotated, o)
    return float(np.sqrt(max(dsq, 0.0)))


def delta_frobenius(
    chain_subject: str, connective: str, chain_object: str, phi_l: PhiLemma
) -> float:
    """Δ via raw multivector coefficient L2.

    Not the principled CGA metric (CLAUDE.md forbids it on hot paths)
    but reported as a sanity check — separation here without
    separation under CGA points to which subspace carries signal.
    """
    s = phi_l(chain_subject)
    o = phi_l(chain_object)
    r = phi_connective(connective)
    s_rotated = _raw_sandwich(r, s)
    return float(np.linalg.norm(s_rotated - o))


# ---------------------------------------------------------------------------
# Pair set — compatible chains + synthesized contradicting twins
# ---------------------------------------------------------------------------
# Compatible chains come from the *actual* reviewed corpus, so we are
# not testing against synthetic data on both sides.
#
# Contradicting twins are formed by swapping the connective with a
# semantic antonym.  The contradiction is structural (same subject,
# same intent, same object, opposite relation).  If φ is sound, the
# rotor should send φ(subject) away from φ(object) under the
# antonym — yielding larger Δ.

_ANTONYMS: dict[str, str] = {
    "requires": "rejects",
    "reveals": "obscures",
    "grounds": "undermines",
    "supports": "contradicts",
    "enables": "prevents",
    "confirms": "refutes",
    "informs": "misleads",
    "verifies": "falsifies",
}


_CHAIN_CORPORA: tuple[Path, ...] = (
    Path("teaching/cognition_chains/cognition_chains_v1.jsonl"),
)


@dataclass(frozen=True)
class Pair:
    chain_id: str
    subject: str
    intent: str
    connective: str
    object: str
    antonym: str


def _load_pairs() -> tuple[Pair, ...]:
    out: list[Pair] = []
    for path in _CHAIN_CORPORA:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            conn = str(row.get("connective", "")).lower()
            antonym = _ANTONYMS.get(conn)
            if antonym is None:
                continue
            out.append(
                Pair(
                    chain_id=str(row["chain_id"]),
                    subject=str(row["subject"]),
                    intent=str(row["intent"]),
                    connective=conn,
                    object=str(row["object"]),
                    antonym=antonym,
                )
            )
    return tuple(out)


# ---------------------------------------------------------------------------
# Separation report
# ---------------------------------------------------------------------------


def _auc(compatible: list[float], contradicting: list[float]) -> float:
    """Rank-based AUC: P(Δ_contradicting > Δ_compatible).

    1.0 = perfect separation (every contradiction Δ greater than
    every compatible Δ).  0.5 = chance.
    """
    if not compatible or not contradicting:
        return float("nan")
    wins = 0
    ties = 0
    total = 0
    for c in compatible:
        for x in contradicting:
            total += 1
            if x > c:
                wins += 1
            elif x == c:
                ties += 1
    return (wins + 0.5 * ties) / total


def _best_threshold_accuracy(
    compatible: list[float], contradicting: list[float]
) -> tuple[float, float]:
    """Sweep thresholds, return (best_accuracy, threshold)."""
    if not compatible or not contradicting:
        return (float("nan"), float("nan"))
    candidates = sorted(set(compatible + contradicting))
    n = len(compatible) + len(contradicting)
    best_acc = 0.0
    best_t = candidates[0]
    for t in candidates:
        # Decision rule: Δ > t ⇒ contradiction.
        correct = sum(1 for c in compatible if c <= t) + sum(
            1 for x in contradicting if x > t
        )
        acc = correct / n
        if acc > best_acc:
            best_acc = acc
            best_t = t
    return (best_acc, float(best_t))


def _summarise(label: str, values: Iterable[float]) -> dict[str, object]:
    arr = np.asarray(list(values), dtype=np.float64)
    return {
        "label": label,
        "n": int(arr.size),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std(ddof=0)),
    }


_PHI_VARIANTS = (
    ("phi.v1.summed_domains", phi_lemma_summed_domains),
    ("phi.v2.centroid_point", phi_lemma_centroid_point),
    ("phi.v3.idf_weighted", phi_lemma_idf_weighted),
    ("phi.v4.idf_centroid", phi_lemma_idf_centroid),
)


def run() -> dict:
    pairs = _load_pairs()
    variants: dict[str, dict] = {}
    for phi_name, phi_l in _PHI_VARIANTS:
        metrics: dict[str, dict] = {}
        for metric_name, fn in (("cga", delta_cga), ("frobenius", delta_frobenius)):
            compat: list[float] = []
            contra: list[float] = []
            for p in pairs:
                compat.append(fn(p.subject, p.connective, p.object, phi_l))
                contra.append(fn(p.subject, p.antonym, p.object, phi_l))
            auc = _auc(compat, contra)
            best_acc, best_t = _best_threshold_accuracy(compat, contra)
            metrics[metric_name] = {
                "compatible": _summarise("compatible", compat),
                "contradicting": _summarise("contradicting", contra),
                "auc": auc,
                "best_threshold": best_t,
                "best_threshold_accuracy": best_acc,
                "promotion_passed": (
                    bool(auc >= 0.80) if not np.isnan(auc) else False
                ),
            }
        variants[phi_name] = metrics
    return {
        "promotion_criterion": "auc >= 0.80",
        "n_pairs": len(pairs),
        "antonym_table": _ANTONYMS,
        "variants": variants,
    }


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
