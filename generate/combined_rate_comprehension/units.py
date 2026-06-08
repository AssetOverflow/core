"""Compound-unit value type for the combined-rate organ (CMB-a).

A combined-rate problem carries two rates over ONE shared compound unit (``rooms/hour``,
``liters/minute``): both contributors are measured the same way, so the model holds a single
``RateUnit``. Two rates with *different* units do not compose — that is a reader refusal
(``rate_unit_mismatch``), representable only because there is one unit slot, not two.

Deliberately a **local** copy of the single-rate organ's ``RateUnit`` rather than an import from
``generate.rate_comprehension`` — the two rate organs are kept disjoint (CMB-a does not depend on
R3) until a shared rate algebra is extracted. The duplication is intentional and tiny; if/when the
rate organs converge (a later slice), promote this to a shared ``rate_algebra`` module and have
both import it. No unit conversion in CMB v1 (mirrors R3's v1 boundary). Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnitError(ValueError):
    """A malformed or non-composing unit — refuse, never fabricate a unit."""


@dataclass(frozen=True, slots=True)
class RateUnit:
    """A compound rate unit ``numerator / denominator`` — ``room/hour``, ``liter/minute``."""

    numerator: str
    denominator: str

    def __post_init__(self) -> None:
        if not self.numerator or not self.denominator:
            raise UnitError(f"RateUnit needs non-empty units; got {self!r}")
        if self.numerator == self.denominator:
            raise UnitError(f"a rate's numerator and denominator must differ; got {self}")

    def __str__(self) -> str:
        return f"{self.numerator}/{self.denominator}"


__all__ = ["RateUnit", "UnitError"]
