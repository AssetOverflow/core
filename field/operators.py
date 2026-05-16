"""
Manifold-level field operators — graph diffusion and protocol.

Operators transform ManifoldState through algebraic transitions.
Diffusion computes a weighted average of each node with its neighbors
in Cl(4,1) component space, then re-unitizes to the versor manifold.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

import numpy as np

from algebra.cl41 import geometric_product
from field.state import ManifoldState


class Operator(Protocol):
    """Protocol for manifold field operators."""

    def forward(self, state: ManifoldState) -> tuple[ManifoldState, float]:
        """Apply operator, return (new_state, delta_norm)."""
        ...

    def adjoint(self) -> Operator:
        """Return the adjoint operator."""
        ...


# Cl(4,1) bivector blade classification for the exponential map.
# Blades 9, 12, 14, 15 square to +1 (boost/hyperbolic planes involving e5).
# Blades 6-8, 10-11, 13 square to -1 (rotation planes).
# Use cosh/sinh for boosts, cos/sin for rotations — mixing them makes
# re-unitization diverge.
_BOOST_INDICES = frozenset({9, 12, 14, 15})


def _unitize_f32(v: np.ndarray) -> np.ndarray:
    """Unitize a multivector to versor condition via the exponential map.

    Builds a proper rotor from the bivector content, ensuring
    R·reverse(R) = 1 exactly in float64, then casts to float32.

    Works in float64 throughout because algebra.backend's Rust
    geometric_product silently returns float32 regardless of input dtype.
    """
    v64 = np.asarray(v, dtype=np.float64)
    norm = float(np.linalg.norm(v64))
    if norm < 1e-12:
        out = np.zeros(32, dtype=np.float32)
        out[0] = 1.0
        return out

    bv = v64[6:16]
    bv_norm = float(np.linalg.norm(bv))
    if bv_norm < 1e-14:
        out = np.zeros(32, dtype=np.float32)
        out[0] = 1.0 if v64[0] >= 0 else -1.0
        return out

    angle = np.arctan2(bv_norm, abs(float(v64[0])))

    rotor = np.zeros(32, dtype=np.float64)
    rotor[0] = 1.0

    for i in range(10):
        w = float(bv[i]) / bv_norm
        if abs(w) < 1e-14:
            continue
        theta = angle * w
        factor = np.zeros(32, dtype=np.float64)
        blade_idx = 6 + i
        if blade_idx in _BOOST_INDICES:
            factor[0] = np.cosh(theta)
            factor[blade_idx] = np.sinh(theta)
        else:
            factor[0] = np.cos(theta)
            factor[blade_idx] = np.sin(theta)
        rotor = geometric_product(rotor, factor)

    if v64[0] < 0:
        rotor = -rotor

    return rotor.astype(np.float32)


class GraphDiffusionOperator:
    """Propagate geometric pressure across graph edges via damped blending.

    Self-adjoint: adjoint() returns self (symmetric diffusion).

    For each node, computes a linear blend with its neighbors in the
    32-component multivector space, then re-projects to the versor
    manifold via the exponential map.  The damping factor controls
    the blend weight: 0 = no change, 1 = replace with neighbor average.
    """

    def __init__(self, damping: float = 0.5) -> None:
        if not 0.0 < damping <= 1.0:
            raise ValueError(f"damping must be in (0, 1], got {damping}")
        self._damping = damping

    def forward(self, state: ManifoldState) -> tuple[ManifoldState, float]:
        old_fields = state.fields

        neighbors: dict[int, list[int]] = defaultdict(list)
        for edge_idx in range(state.edges.shape[0]):
            src, dst = int(state.edges[edge_idx, 0]), int(state.edges[edge_idx, 1])
            neighbors[dst].append(src)

        new_fields = old_fields.copy()
        for node, srcs in neighbors.items():
            f = old_fields[node].astype(np.float64)
            neighbor_avg = np.mean(
                [old_fields[s].astype(np.float64) for s in srcs], axis=0,
            )
            blended = (1.0 - self._damping) * f + self._damping * neighbor_avg
            new_fields[node] = _unitize_f32(blended)

        delta = float(np.linalg.norm(new_fields - old_fields))
        return ManifoldState(fields=new_fields, edges=state.edges, step=state.step + 1), delta

    def adjoint(self) -> GraphDiffusionOperator:
        return self
