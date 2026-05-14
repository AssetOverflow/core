"""core.physics.digest — Digest cycles: integration of BindingFrames into FieldState.

ADR-0009: A DigestCycle integrates a BindingFrame into the existing
FieldState as consolidated pressure via coherence wave propagation.
Propagation-over-mutation: the digest operator does not rewrite field
regions. It propagates a coherence wave outward from the binding frame.
"""

from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from field.state import FieldState


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
        coherence = max(0.0, min(1.0, float(binding_frame.coherence_magnitude)))
        budget = max(0.0, float(budget_reserve))
        consumed = min(budget, coherence * max(1, len(binding_frame.region_ids)))
        radius = consumed / max(1, len(binding_frame.region_ids))
        updated = FieldState(
            F=np.asarray(field_state.F).copy(),
            node=field_state.node,
            step=field_state.step + 1,
            holonomy=field_state.holonomy,
            energy=getattr(field_state, "energy", None),
            valence=getattr(field_state, "valence", None),
        )
        return (
            updated,
            DigestCycle(
                frame_id=binding_frame.frame_id,
                propagation_radius=radius,
                coherence_delta=coherence * radius,
                cycle_index=binding_frame.cycle_index,
                budget_consumed=consumed,
            ),
        )
