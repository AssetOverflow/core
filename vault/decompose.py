"""
vault/decompose.py — FieldDecomposer and UnknownDomainGate

When VaultStore.recall() returns no results above the coherence floor for a
query versor, this module provides two complementary mechanisms:

1.  FieldDecomposer
    Decomposes the query versor into its top-3 grade components
    (scalar, vector, bivector) in Cl(4,1) and recalls each component
    separately from the vault.  The results are blended by component
    norm weight, giving a composed recall even for novel query points
    that have no direct vault entry.  This is the geometric
    generalisation mechanism — unknown concepts return a weighted
    combination of familiar field directions.

2.  UnknownDomainGate
    If the best recall score across both direct and decomposed recall
    is below UNKNOWN_FLOOR, the gate fires.  ChatRuntime checks the gate
    before proposition formation and routes to a safe "I don't have field
    coordinates for that" surface rather than fabricating a low-confidence
    answer.

Grade structure for Cl(4,1), 32-dimensional multivector
--------------------------------------------------------
Grade 0 (scalar):   index 0             →  1 component
Grade 1 (vector):   indices 1-5         →  5 components  (e1..e4, e_inf or e0)
Grade 2 (bivector): indices 6-15        → 10 components
Grade 3 (trivector):indices 16-25       → 10 components
Grade 4:            indices 26-30       →  5 components
Grade 5 (pseudoscalar): index 31        →  1 component

We decompose into grades 0-2 because they carry the bulk of CGA point/
direction/circle semantics.  Grades 3-5 are preserved as a residual.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from vault.store import VaultStore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Minimum best-match score to consider recall meaningful.
#: Below this, UnknownDomainGate fires.
UNKNOWN_FLOOR: float = 0.15

#: Grade slice boundaries for a 32-dim Cl(4,1) multivector.
_GRADE_SLICES: tuple[tuple[int, int], ...] = (
    (0, 1),    # grade 0 — scalar
    (1, 6),    # grade 1 — vector
    (6, 16),   # grade 2 — bivector
)


# ---------------------------------------------------------------------------
# FieldDecomposer
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DecomposedRecallResult:
    """Aggregated recall from grade-split decomposition."""
    hits: list[dict]          # merged, weight-sorted recall hits
    best_score: float         # highest individual component score
    component_scores: tuple[float, ...]  # one score per grade component
    unknown: bool             # True if best_score < UNKNOWN_FLOOR


class FieldDecomposer:
    """
    Decomposes a query versor into grade components and recalls each
    from a VaultStore, then blends the results by component norm.
    """

    def recall(
        self,
        vault: "VaultStore",
        query: np.ndarray,
        top_k: int = 5,
    ) -> DecomposedRecallResult:
        """
        Parameters
        ----------
        vault   : VaultStore instance to query
        query   : 1-D float32 array of length 32 (Cl(4,1) multivector)
        top_k   : results per grade component; final list deduped and trimmed

        Returns
        -------
        DecomposedRecallResult
        """
        q = np.asarray(query, dtype=np.float32)
        if q.ndim != 1:
            raise ValueError(f"query must be 1-D, got shape {q.shape}")
        q_len = q.shape[0]

        component_scores: list[float] = []
        component_hits: list[list[dict]] = []
        component_weights: list[float] = []

        for start, end in _GRADE_SLICES:
            if start >= q_len:
                continue
            end_clamped = min(end, q_len)
            grade_vec = np.zeros(q_len, dtype=np.float32)
            grade_vec[start:end_clamped] = q[start:end_clamped]
            norm = float(np.linalg.norm(grade_vec))
            if norm < 1e-8:
                component_scores.append(0.0)
                component_hits.append([])
                component_weights.append(0.0)
                continue

            # INV-24 recall role: RECOGNITION.  Grade-decomposed fallback for
            # UnknownDomainGate when direct recall scores below the floor —
            # still a "have we seen this?" probe, not evidence admission.
            hits = vault.recall(grade_vec, top_k=top_k)
            best = max((h["score"] for h in hits), default=0.0)
            component_scores.append(best)
            component_hits.append(hits)
            component_weights.append(norm)

        # Blend results: weight each hit list by its component's vector norm.
        # Deduplicate by vault index, keeping the highest weighted score.
        total_weight = sum(component_weights) or 1.0
        merged: dict[int, dict] = {}
        for hits, w in zip(component_hits, component_weights):
            rel_w = w / total_weight
            for h in hits:
                idx = h["index"]
                weighted_score = h["score"] * rel_w
                if idx not in merged or merged[idx]["score"] < weighted_score:
                    merged[idx] = {
                        "versor":   h["versor"],
                        "score":    weighted_score,
                        "metadata": h["metadata"],
                        "index":    idx,
                    }

        sorted_hits = sorted(merged.values(), key=lambda h: h["score"], reverse=True)
        best_score = sorted_hits[0]["score"] if sorted_hits else 0.0

        return DecomposedRecallResult(
            hits=sorted_hits[:top_k],
            best_score=best_score,
            component_scores=tuple(component_scores),
            unknown=best_score < UNKNOWN_FLOOR,
        )


# ---------------------------------------------------------------------------
# UnknownDomainGate
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GateDecision:
    """Result of an UnknownDomainGate check."""
    fire: bool          # True → query is outside known domain
    best_score: float   # best recall score seen
    source: str         # "direct" | "decomposed" | "empty_vault"


class UnknownDomainGate:
    """
    Checks whether a query versor falls outside the vault's known domain.

    Usage in ChatRuntime.chat()
    ---------------------------
    gate = UnknownDomainGate()
    decomposer = FieldDecomposer()

    direct_hits = ctx.vault.recall(query_F, top_k=3)
    direct_best = max((h["score"] for h in direct_hits), default=0.0)

    decision = gate.check(direct_best, vault=ctx.vault, query=query_F, decomposer=decomposer)
    if decision.fire:
        return _unknown_domain_response()   # safe surface, no fabrication
    """

    def __init__(self, floor: float = UNKNOWN_FLOOR) -> None:
        self._floor = floor

    def check(
        self,
        direct_best_score: float,
        vault: "VaultStore",
        query: np.ndarray,
        decomposer: FieldDecomposer | None = None,
    ) -> GateDecision:
        """
        Returns a GateDecision.  If the vault is empty, fires immediately.
        If direct recall passes the floor, clears immediately.
        Otherwise, falls back to decomposed recall.
        """
        if len(vault) == 0:
            return GateDecision(fire=True, best_score=0.0, source="empty_vault")

        if direct_best_score >= self._floor:
            return GateDecision(fire=False, best_score=direct_best_score, source="direct")

        # Attempt decomposed recall as fallback
        if decomposer is not None:
            result = decomposer.recall(vault, query, top_k=3)
            if not result.unknown:
                return GateDecision(fire=False, best_score=result.best_score, source="decomposed")
            return GateDecision(fire=True, best_score=result.best_score, source="decomposed")

        return GateDecision(fire=True, best_score=direct_best_score, source="direct")


# ---------------------------------------------------------------------------
# Module-level default instances (stateless — safe to share)
# ---------------------------------------------------------------------------

default_decomposer = FieldDecomposer()
default_gate = UnknownDomainGate()
