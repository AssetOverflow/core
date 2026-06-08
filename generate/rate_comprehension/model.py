"""Typed model for an R3 single-rate problem (R3b).

A single-rate problem is the fixed equation ``quantity = rate × time`` with **exactly one**
unknown (the query). ``rate_unit`` (e.g. ``mile/hour``) is the single source of unit truth: the
quantity is measured in ``rate_unit.numerator`` and the time in ``rate_unit.denominator``, so the
three units are consistent by construction. The two non-query slots carry integer values; the
query slot is ``None``.

Pure data with a structural guard: exactly the query slot is unknown (illegal states — zero or two
unknowns — cannot be represented). Off-serving; deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from generate.rate_comprehension.units import RateUnit

RateRole = Literal["rate", "time", "quantity"]


@dataclass(frozen=True, slots=True)
class RateProblem:
    """``quantity = rate × time`` with one unknown. ``rate_unit`` fixes all three units."""

    rate_unit: RateUnit
    rate: int | None
    time: int | None
    quantity: int | None
    query: RateRole
    #: The duration's ORIGINAL time unit from the text (R3.2). Defaults to the rate's denominator
    #: (the non-converting case); a convertible duration (e.g. ``minute`` vs a ``/hour`` rate)
    #: keeps its original unit here and the SOLVER converts it. ``time`` stays the original int.
    time_unit: str | None = None

    def __post_init__(self) -> None:
        if self.time_unit is None:
            object.__setattr__(self, "time_unit", self.rate_unit.denominator)
        slots: dict[str, int | None] = {"rate": self.rate, "time": self.time, "quantity": self.quantity}
        unknown = [role for role, value in slots.items() if value is None]
        if unknown != [self.query]:
            raise ValueError(
                f"exactly the query slot must be the unknown; query={self.query!r}, unknown={unknown}"
            )
        for role, value in slots.items():
            if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
                raise ValueError(f"{role} value must be int; got {value!r}")

    @property
    def quantity_unit(self) -> str:
        return self.rate_unit.numerator


__all__ = ["RateProblem", "RateRole"]
