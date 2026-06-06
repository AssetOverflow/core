"""Edge-deployment budget lane (A2 of the refined sequencing).

Proves — deterministically, not by assertion — what a long-running CORE life costs to
persist per turn on a constrained, offline, no-GPU device. The gate encodes the edge
REQUIREMENT (bounded per-turn checkpoint cost) and currently fails it (the O(n)
persistence cliff), flipping green only when incremental/append-only persistence lands.
"""

from evals.edge_budget.runner import (
    DEFAULT_TURNS,
    EDGE_PER_TURN_CEILING_BYTES,
    REGRESSION_PER_TURN_CEILING_BYTES,
    REGRESSION_TOTAL_CEILING_BYTES,
    TurnCost,
    measure,
    run,
)

__all__ = [
    "DEFAULT_TURNS",
    "EDGE_PER_TURN_CEILING_BYTES",
    "REGRESSION_PER_TURN_CEILING_BYTES",
    "REGRESSION_TOTAL_CEILING_BYTES",
    "TurnCost",
    "measure",
    "run",
]
