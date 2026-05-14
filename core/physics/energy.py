"""core.physics.energy — ADR-0006 scalar companion classes.

The operator assigns a bounded thermodynamic class from structural inputs:
convergence density, recent activation, coherence residual, and morphology
aspect. It does not inspect grades, repair fields, or normalize anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import exp, log1p
from typing import Mapping


class EnergyClass(str, Enum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"

    @property
    def vault_candidate(self) -> bool:
        return self in {EnergyClass.E0, EnergyClass.E1}

    @property
    def governance_critical(self) -> bool:
        return self is EnergyClass.E4


@dataclass(frozen=True, slots=True)
class EnergyProfile:
    raw: float
    energy_class: EnergyClass
    convergence_density: int = 0
    activation_count: int = 0
    last_activation_cycle: int = 0
    coherence_residual: float = 0.0
    aspect_weight: float = 0.0
    anchor_adjacent: bool = False

    @property
    def requires_architect_review(self) -> bool:
        return self.energy_class.governance_critical or (
            self.anchor_adjacent and self.energy_class in {EnergyClass.E3, EnergyClass.E4}
        )


_ASPECT_WEIGHTS: dict[str, float] = {
    "qatal": 0.15,
    "aorist": 0.15,
    "wayyiqtol": 0.45,
    "perfect": 0.25,
    "yiqtol": 0.65,
    "imperfect": 0.70,
    "present": 0.65,
    "cohortative": 0.55,
    "optative": 0.50,
    "imperative": 0.90,
    "jussive": 0.60,
    "subjunctive": 0.55,
}


def aspect_weight(features: Mapping[str, object] | None) -> float:
    if not features:
        return 0.0
    values = [
        str(value).lower()
        for key, value in features.items()
        if key in {"aspect", "tense", "mood"}
    ]
    return max((_ASPECT_WEIGHTS.get(value, 0.0) for value in values), default=0.0)


class FieldEnergyOperator:
    """Compute ADR-0006 energy class from explicit structural inputs."""

    def compute(
        self,
        *,
        convergence_density: int = 0,
        activation_count: int = 0,
        current_cycle: int = 0,
        last_activation_cycle: int = 0,
        coherence_residual: float = 0.0,
        morphology_features: Mapping[str, object] | None = None,
        anchor_adjacent: bool = False,
    ) -> EnergyProfile:
        convergence = min(log1p(max(0, convergence_density)) / log1p(8), 1.0)
        age = max(0, int(current_cycle) - int(last_activation_cycle))
        recency = min(max(0, activation_count), 8) / 8.0 * exp(-age / 12.0)
        residual = min(max(0.0, float(coherence_residual)), 1.0)
        aspect = aspect_weight(morphology_features)
        raw = (0.35 * convergence) + (0.25 * recency) + (0.20 * residual) + (0.20 * aspect)
        if anchor_adjacent and raw >= 0.72:
            energy_class = EnergyClass.E4
        elif raw >= 0.82:
            energy_class = EnergyClass.E4
        elif raw >= 0.62:
            energy_class = EnergyClass.E3
        elif raw >= 0.38:
            energy_class = EnergyClass.E2
        elif raw >= 0.16:
            energy_class = EnergyClass.E1
        else:
            energy_class = EnergyClass.E0
        return EnergyProfile(
            raw=raw,
            energy_class=energy_class,
            convergence_density=max(0, convergence_density),
            activation_count=max(0, activation_count),
            last_activation_cycle=max(0, last_activation_cycle),
            coherence_residual=residual,
            aspect_weight=aspect,
            anchor_adjacent=anchor_adjacent,
        )
