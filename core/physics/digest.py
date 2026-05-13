"""core.physics.digest — Digest cycles: integration of BindingFrames into FieldState.

ADR-0009: A DigestCycle integrates a BindingFrame into the existing
FieldState as consolidated pressure via coherence wave propagation.
Propagation-over-mutation: the digest operator does not rewrite field
regions. It propagates a coherence wave outward from the binding frame.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class DigestCycle:
    """Record of a single digest operation."""
    frame_id: str           # ID of the BindingFrame being digested
    propagation_radius: float
    coherence_delta: float  # net change in field coherence after digest
    cycle_index: int
    budget_consumed: float  # drawn from CoherenceBudget.reserve


class DigestOperator:
    """Integrates a BindingFrame into FieldState via coherence wave propagation.

    Rust acceleration target: core_rs::physics::digest::propagate_wave
    """

    def digest(self, binding_frame, field_state, budget_reserve: float) -> tuple:
        """Returns (updated_field_state, DigestCycle)."""
        raise NotImplementedError(
            "DigestOperator.digest: implement coherence wave propagation"
        )
