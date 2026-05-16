"""
Manifold-level field operators — graph diffusion and dual-correction.

Two operators implement Axiom 4 (Dual-Correction):

  GraphDiffusionOperator   — forward pass: spread context pressure across
                             edges via damped blending + exponential-map
                             re-unitization.  Self-adjoint.

  ConstraintCorrectionOperator — adjoint pass: apply an incremental
                             correction rotor on the output node, pulling
                             it toward the intent-target versor built from
                             the prompt centroid.  Non-self-adjoint.

Coupled loop (V4 pulse):

    while not converged:
        state, delta_fwd  = diffusion_op.forward(state)
        state, delta_corr = correction_op.adjoint_pass(state)
        converged = delta_fwd < eps and delta_corr < eps

The target is always the same centroid versor that initialised the output
node — diffusion spreads context away from it; correction pulls it back
while incorporating neighbour pressure.  The system argues with itself
until both forces balance.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

import numpy as np

from algebra.backend import (
    diffusion_step as _rust_diffusion_step,
    unitize_expmap as _rust_unitize,
)
from algebra.cl41 import geometric_product, reverse
from field.state import ManifoldState


class Operator(Protocol):
    """Protocol for manifold field operators."""

    def forward(self, state: ManifoldState) -> tuple[ManifoldState, float]:
        """Apply operator, return (new_state, delta_norm)."""
        ...

    def adjoint(self) -> "Operator":
        """Return the adjoint operator."""
        ...


# ---------------------------------------------------------------------------
# Blade classification for the exponential map in Cl(4,1).
#
# Blades 9, 12, 14, 15 square to +1 (boost/hyperbolic planes involving e5).
# Blades 6-8, 10-11, 13 square to -1 (rotation planes).
# Use cosh/sinh for boosts, cos/sin for rotations.
# Mixing them causes re-unitization to diverge rather than converge.
# This set was determined empirically by checking which blades satisfy
# e_i * e_i = +1 under the Cl(4,1) metric (+,+,+,+,-) and the specific
# basis ordering used in algebra/cl41.py.
# ---------------------------------------------------------------------------
_BOOST_INDICES = frozenset({9, 12, 14, 15})


def _unitize_f32(v: np.ndarray) -> np.ndarray:
    """Unitize a multivector to versor condition via the exponential map.

    Builds a proper rotor from the bivector content, ensuring
    R·reverse(R) = 1 exactly in float64, then casts to float32.

    Uses the Rust backend when available for the hot path.
    """
    rust_result = _rust_unitize(np.asarray(v, dtype=np.float32))
    if rust_result is not None:
        return rust_result

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


def _incremental_correction_rotor(
    current: np.ndarray,
    target: np.ndarray,
    rate: float,
) -> np.ndarray:
    """Build a small rotor that nudges `current` incrementally toward `target`.

    Rather than computing the full transition rotor (which would jump the
    output node all the way to the target in one step and destroy context
    pressure from diffusion), we build an incremental step:

        blended = (1 - rate) * current + rate * target

    then close the blend via the exponential map.  The correction_rate
    controls how much the output node is pulled per iteration.  At rate=0
    the output is unchanged; at rate=1 the output node collapses to the
    target immediately (collapsing context — not useful).

    This is intentionally the same blend-then-unitize pattern used in
    GraphDiffusionOperator.forward(), which is why both operators converge
    to the same fixed-point attractor when their forces balance.
    """
    c64 = np.asarray(current, dtype=np.float64)
    t64 = np.asarray(target,  dtype=np.float64)
    blended = (1.0 - rate) * c64 + rate * t64
    return _unitize_f32(blended)


# ---------------------------------------------------------------------------
# GraphDiffusionOperator — forward pass, self-adjoint
# ---------------------------------------------------------------------------

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
        # Try Rust batch path first
        rust_result = _rust_diffusion_step(state.fields, state.edges, self._damping)
        if rust_result is not None:
            new_fields, delta = rust_result
            return ManifoldState(fields=new_fields, edges=state.edges, step=state.step + 1), delta

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

    def adjoint(self) -> "GraphDiffusionOperator":
        return self


# ---------------------------------------------------------------------------
# ConstraintCorrectionOperator — adjoint pass, non-self-adjoint
# ---------------------------------------------------------------------------

class ConstraintCorrectionOperator:
    """Pull the output node toward the intent-target versor.

    This is the non-trivial adjoint operator that implements Axiom 4
    (Dual-Correction).  GraphDiffusionOperator spreads context pressure
    outward across the graph; ConstraintCorrectionOperator restores
    intent coherence by pulling the designated output node back toward
    the target established from the input prompt.

    Unlike GraphDiffusionOperator, this operator is NOT self-adjoint:
    it has a preferred direction (toward the target).  Its adjoint() is
    the identity (no forward pass — it only acts on the adjoint path).

    The coupling of these two operators in the pulse loop is the closed
    loop described in CORE architecture docs:
      - Diffusion spreads context (breaks intent coherence slightly)
      - Correction restores intent (breaks pure diffusion symmetry)
      - They converge to a fixed-point that balances both pressures

    Parameters
    ----------
    target_versor   : The intent target — the centroid versor built from
                      the prompt tokens.  This is the same versor that
                      initialises the output node before diffusion begins.
    correction_rate : Blend weight toward target per adjoint_pass call.
                      In (0, 1].  Default 0.3.  Lower = smoother correction,
                      more steps to converge.  Higher = faster but risks
                      overriding context pressure from diffusion.
    node_index      : Which node in the ManifoldState to correct.
                      Default -1 (last node = output node in V4 topology).
    """

    def __init__(
        self,
        target_versor: np.ndarray,
        correction_rate: float = 0.3,
        node_index: int = -1,
    ) -> None:
        if not 0.0 < correction_rate <= 1.0:
            raise ValueError(
                f"correction_rate must be in (0, 1], got {correction_rate}"
            )
        self._target = np.asarray(target_versor, dtype=np.float32).copy()
        self._rate   = float(correction_rate)
        self._node   = int(node_index)

    @property
    def target_versor(self) -> np.ndarray:
        """Return a copy of the intent-target versor."""
        return self._target.copy()

    def adjoint_pass(
        self, state: ManifoldState
    ) -> tuple[ManifoldState, float]:
        """Apply one incremental correction step to the output node.

        Computes a blended versor between the current output-node field
        and the intent target, closes it via _unitize_f32, and replaces
        the output node in a new ManifoldState.

        Returns (new_state, delta) where delta is the L2 norm of the
        change on the output node only.  Convergence is signalled when
        delta < threshold, meaning the output node has settled into a
        stable compromise between context pressure and intent pull.
        """
        node_idx = self._node % state.fields.shape[0]
        old_fields  = state.fields
        current = old_fields[node_idx]

        corrected = _incremental_correction_rotor(current, self._target, self._rate)

        new_fields = old_fields.copy()
        new_fields[node_idx] = corrected

        delta = float(np.linalg.norm(corrected.astype(np.float64) - current.astype(np.float64)))
        return (
            ManifoldState(fields=new_fields, edges=state.edges, step=state.step),
            delta,
        )

    def forward(self, state: ManifoldState) -> tuple[ManifoldState, float]:
        """Identity forward pass — correction acts only on the adjoint path."""
        return state, 0.0

    def adjoint(self) -> "ConstraintCorrectionOperator":
        """Return self — the operator IS the adjoint pass."""
        return self
