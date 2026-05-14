"""Measured holonomy-resonance evidence helpers for ADR-0015."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from algebra.cga import cga_inner
from algebra.holonomy import holonomy_encode


@dataclass(frozen=True, slots=True)
class ResonanceEvidence:
    case_id: str
    aligned_score: float
    contrast_score: float

    @property
    def passes(self) -> bool:
        return self.aligned_score > self.contrast_score


def encode_clause(manifold, tokens: tuple[str, ...] | list[str]) -> np.ndarray:
    return holonomy_encode([manifold.get_versor(token) for token in tokens])


def mean_pair_score(manifold, pairs: tuple[tuple[str, str], ...]) -> float:
    if not pairs:
        return 0.0
    return float(
        np.mean(
            [
                cga_inner(manifold.get_versor(left), manifold.get_versor(right))
                for left, right in pairs
            ]
        )
    )


def resonance_evidence(
    *,
    case_id: str,
    manifold,
    aligned_pairs: tuple[tuple[str, str], ...],
    contrast_pairs: tuple[tuple[str, str], ...],
) -> ResonanceEvidence:
    return ResonanceEvidence(
        case_id=case_id,
        aligned_score=mean_pair_score(manifold, aligned_pairs),
        contrast_score=mean_pair_score(manifold, contrast_pairs),
    )
