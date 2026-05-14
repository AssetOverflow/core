"""core.physics.learning — ADR-0014 vault promotion criteria."""

from __future__ import annotations

from dataclasses import dataclass

from core.physics.energy import EnergyClass, EnergyProfile


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    promote: bool
    reason: str
    energy_class: EnergyClass


class VaultPromotionPolicy:
    """Promote only settled, coherent regions into deep vault storage."""

    def __init__(self, residual_threshold: float = 0.05) -> None:
        if residual_threshold < 0.0:
            raise ValueError("residual_threshold must be non-negative")
        self.residual_threshold = float(residual_threshold)

    def decide(self, energy: EnergyProfile | None) -> PromotionDecision:
        if energy is None:
            return PromotionDecision(False, "missing_energy_profile", EnergyClass.E2)
        if not energy.energy_class.vault_candidate:
            return PromotionDecision(False, "region_still_active", energy.energy_class)
        if energy.coherence_residual > self.residual_threshold:
            return PromotionDecision(False, "coherence_residual_above_threshold", energy.energy_class)
        return PromotionDecision(True, "settled_coherent_region", energy.energy_class)
