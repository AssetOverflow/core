"""Calibration parameter space — bounded, deterministic, immutable."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True, slots=True)
class CalibrationParams:
    salience_top_k: int = 16
    inhibition_threshold: float = 0.3
    teaching_retrieval_limit: int = 8

    def as_dict(self) -> dict[str, int | float]:
        return {
            "salience_top_k": self.salience_top_k,
            "inhibition_threshold": self.inhibition_threshold,
            "teaching_retrieval_limit": self.teaching_retrieval_limit,
        }


DEFAULT_PARAMS = CalibrationParams()

PARAM_GRID: dict[str, tuple] = {
    "salience_top_k": (8, 12, 16),
    "inhibition_threshold": (0.2, 0.3, 0.4),
}


def grid_candidates(
    grid: dict[str, tuple] | None = None,
    base: CalibrationParams = DEFAULT_PARAMS,
) -> tuple[CalibrationParams, ...]:
    """Generate all candidate parameter sets from a grid.

    Each candidate varies exactly one axis from the base; the grid is
    a deterministic Cartesian product over the provided axes.
    """
    g = grid or PARAM_GRID
    keys = sorted(g.keys())
    values = [g[k] for k in keys]
    candidates = []
    for combo in product(*values):
        overrides = dict(zip(keys, combo))
        candidate = CalibrationParams(
            salience_top_k=overrides.get("salience_top_k", base.salience_top_k),
            inhibition_threshold=overrides.get("inhibition_threshold", base.inhibition_threshold),
            teaching_retrieval_limit=base.teaching_retrieval_limit,
        )
        candidates.append(candidate)
    return tuple(candidates)
