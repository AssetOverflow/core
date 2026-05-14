from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from generate.salience import SalienceMap
from vocab.manifold import VocabManifold


@dataclass(frozen=True, slots=True)
class AttentionPlan:
    allowed_indices: np.ndarray
    salience_map: SalienceMap

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_indices", np.asarray(self.allowed_indices, dtype=np.int64).copy())


class AttentionOperator:
    """
    Convert SalienceMap to AttentionPlan by applying budget and inhibition.

    Inhibition excludes indices whose score is below max_score * threshold,
    removing the weak long-tail of manifold points before generation walks.
    """

    def __init__(self, inhibition_threshold: float = 0.3) -> None:
        if inhibition_threshold < 0.0:
            raise ValueError("inhibition_threshold must be non-negative")
        self.inhibition_threshold = float(inhibition_threshold)

    def plan(self, salience: SalienceMap, vocab: VocabManifold) -> AttentionPlan:
        if len(salience.indices) == 0:
            return AttentionPlan(allowed_indices=np.asarray([], dtype=np.int64), salience_map=salience)
        max_score = float(salience.scores[0])
        threshold = max_score * self.inhibition_threshold
        mask = salience.scores >= threshold
        allowed = salience.indices[mask]
        if len(allowed) == 0:
            allowed = salience.indices[:1]
        allowed = allowed[: min(len(allowed), salience.budget, len(vocab))]
        return AttentionPlan(allowed_indices=allowed, salience_map=salience)
