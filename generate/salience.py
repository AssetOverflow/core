from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from algebra.backend import cga_inner
from core.physics.salience import FieldRegion, SalienceOperator as CurvatureSalienceOperator
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
    Compute generation-facing salience from ADR-0008 field curvature.

    The live API still returns manifold indices for generation, but the score is
    now a local curvature magnitude from core.physics.salience rather than
    normalized proximity to the query field.
    """

    def compute(self, field: FieldState, vocab: VocabManifold, top_k: int = 16) -> SalienceMap:
        if top_k <= 0:
            return SalienceMap(indices=np.asarray([], dtype=np.int64), scores=np.asarray([], dtype=np.float32), budget=0)
        if len(vocab) == 0:
            return SalienceMap(indices=np.asarray([], dtype=np.int64), scores=np.asarray([], dtype=np.float32), budget=0)

        active = vocab.get_versor_at(field.node)
        regions: list[FieldRegion] = []
        for idx in range(len(vocab)):
            v = vocab.get_versor_at(idx)
            energy = vocab.energy_for_word(vocab.get_word_at(idx))
            baseline = energy.raw if energy is not None else 0.1
            active_distance = max(0.0, -2.0 * float(cga_inner(active, v)))
            pressure = baseline + (1.0 / (1.0 + active_distance))
            regions.append(
                FieldRegion(
                    region_id=str(idx),
                    coordinates=tuple(float(x) for x in np.asarray(v, dtype=np.float32)),
                    pressure_magnitude=pressure,
                )
            )

        curvature = CurvatureSalienceOperator().compute(tuple(regions), cycle_index=field.step)
        scores_arr = np.zeros(len(vocab), dtype=np.float32)
        for entry in curvature.entries:
            scores_arr[int(entry.region_id)] = float(entry.curvature_magnitude)
        k = min(int(top_k), len(vocab))
        order = np.argsort(-scores_arr, kind="stable")[:k]
        return SalienceMap(indices=order.astype(np.int64), scores=scores_arr[order], budget=k)
