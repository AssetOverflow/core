"""
Manifold-level field operators — graph diffusion and protocol.

Operators transform ManifoldState through algebraic transitions.
construction_seed_versor is used here as a construction primitive (building new
versors from damped blends), not as propagation repair.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from algebra.backend import versor_apply
from algebra.rotor import word_transition_rotor
from algebra.versor import construction_seed_versor
from field.state import ManifoldState


class Operator(Protocol):
    """Protocol for manifold field operators."""

    def forward(self, state: ManifoldState) -> tuple[ManifoldState, float]:
        """Apply operator, return (new_state, delta_norm)."""
        ...

    def adjoint(self) -> Operator:
        """Return the adjoint operator."""
        ...


class GraphDiffusionOperator:
    """Propagate geometric pressure across graph edges via damped versor transitions.

    Self-adjoint: adjoint() returns self (symmetric diffusion).
    Uses construction-tier construction_seed_versor for post-damping closure.
    """

    def __init__(self, damping: float = 0.5) -> None:
        if not 0.0 < damping <= 1.0:
            raise ValueError(f"damping must be in (0, 1], got {damping}")
        self._damping = damping

    def forward(self, state: ManifoldState) -> tuple[ManifoldState, float]:
        old_fields = state.fields
        new_fields = old_fields.copy()

        for edge_idx in range(state.edges.shape[0]):
            src, dst = int(state.edges[edge_idx, 0]), int(state.edges[edge_idx, 1])
            try:
                V = word_transition_rotor(old_fields[src], old_fields[dst])
            except ValueError:
                continue
            diffused = versor_apply(V, old_fields[dst])
            blended = self._damping * diffused + (1.0 - self._damping) * old_fields[dst]
            try:
                new_fields[dst] = construction_seed_versor(blended)
            except ValueError:
                new_fields[dst] = old_fields[dst]

        delta = float(np.linalg.norm(new_fields - old_fields))
        return ManifoldState(fields=new_fields, edges=state.edges, step=state.step + 1), delta

    def adjoint(self) -> GraphDiffusionOperator:
        return self
