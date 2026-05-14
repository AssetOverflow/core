from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from algebra.backend import cga_inner
from field.state import FieldState
from vocab.manifold import VocabManifold


@dataclass(frozen=True, slots=True)
class SalienceMap:
    indices: np.ndarray
    scores: np.ndarray
    budget: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "indices", np.asarray(self.indices, dtype=np.int64).copy())
        object.__setattr__(self, "scores", np.asarray(self.scores, dtype=np.float32).copy())
        object.__setattr__(self, "budget", int(self.budget))


class SalienceOperator:
    """
    Compute geometric salience of manifold points relative to current FieldState.

    Salience is field-relative CGA activation:
        salience(v_i) = |cga_inner(F, v_i)| / (||F|| * ||v_i||)

    No learned weights. No softmax. Pure geometry routed through algebra.backend,
    which uses core_rs when active.
    """

    def compute(self, field: FieldState, vocab: VocabManifold, top_k: int = 16) -> SalienceMap:
        if top_k <= 0:
            return SalienceMap(indices=np.asarray([], dtype=np.int64), scores=np.asarray([], dtype=np.float32), budget=0)
        if len(vocab) == 0:
            return SalienceMap(indices=np.asarray([], dtype=np.int64), scores=np.asarray([], dtype=np.float32), budget=0)

        query = np.asarray(field.F, dtype=np.float32)
        query_norm = max(float(np.linalg.norm(query)), 1e-8)
        scores: list[float] = []
        for idx in range(len(vocab)):
            v = vocab.get_versor_at(idx)
            denom = query_norm * max(float(np.linalg.norm(v)), 1e-8)
            scores.append(abs(float(cga_inner(query, v))) / denom)

        scores_arr = np.asarray(scores, dtype=np.float32)
        k = min(int(top_k), len(vocab))
        order = np.argsort(-scores_arr, kind="stable")[:k]
        return SalienceMap(indices=order.astype(np.int64), scores=scores_arr[order], budget=k)
