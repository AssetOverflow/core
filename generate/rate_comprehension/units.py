"""Compound-unit algebra for the R3 single-rate organ (R3a).

The genuinely new substrate of R3: a **rate carries a compound unit** — ``mile/hour`` is
``quantity / time`` — and the three single-rate operations must verify that units *compose*:

```text
rate × time      ->  quantity   (mile/hour × hour = mile)      [time must be the rate's denominator]
quantity ÷ time  ->  rate       (mile ÷ hour = mile/hour)
quantity ÷ rate  ->  time       (mile ÷ mile/hour = hour)      [quantity must be the rate's numerator]
```

A non-composing operation REFUSES (``UnitError``) rather than producing a nonsense unit —
``mile/hour × minute``, ``students/hour × mile``, ``dollar ÷ mile/hour``. This is the wrong=0
boundary for R3: the dimensional check refuses before any arithmetic runs.

Deliberately tiny. Units are bare names; there is **no** generic dimensional-analysis universe
and **no** semantic unit-class typing (v1 cannot itself know "dollar is not a time" — the gold and
reader only admit sensible single-rate problems). Compound-of-compound and rate/rate are simply
not representable (``RateUnit`` is one numerator over one denominator). No unit conversion (v1
never turns minutes into hours). Deterministic; no clock, no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnitError(ValueError):
    """A non-composing unit operation — refuse, never fabricate a unit."""


@dataclass(frozen=True, slots=True)
class BaseUnit:
    """A simple unit of quantity or time — ``mile``, ``hour``, ``dollar``, ``widget``."""

    name: str

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise UnitError(f"BaseUnit needs a non-empty name; got {self.name!r}")


@dataclass(frozen=True, slots=True)
class RateUnit:
    """A compound rate unit ``numerator / denominator`` — ``mile/hour``, ``dollar/hour``."""

    numerator: str
    denominator: str

    def __post_init__(self) -> None:
        if not self.numerator or not self.denominator:
            raise UnitError(f"RateUnit needs non-empty units; got {self!r}")
        if self.numerator == self.denominator:
            raise UnitError(f"a rate's numerator and denominator must differ; got {self}")

    def __str__(self) -> str:
        return f"{self.numerator}/{self.denominator}"


def rate_times_time(rate: RateUnit, time: BaseUnit) -> BaseUnit:
    """``rate × time -> quantity`` (``mile/hour × hour = mile``). The time unit MUST be the rate's
    denominator, else REFUSE (``mile/hour × minute``)."""
    if time.name != rate.denominator:
        raise UnitError(f"{rate} × {time.name}: the time unit must be {rate.denominator!r}")
    return BaseUnit(rate.numerator)


def rate_from_quantity_over_time(quantity: BaseUnit, time: BaseUnit) -> RateUnit:
    """``quantity ÷ time -> rate`` (``mile ÷ hour = mile/hour``)."""
    if quantity.name == time.name:
        raise UnitError(f"{quantity.name} ÷ {time.name}: quantity and time units must differ")
    return RateUnit(quantity.name, time.name)


def time_from_quantity_over_rate(quantity: BaseUnit, rate: RateUnit) -> BaseUnit:
    """``quantity ÷ rate -> time`` (``mile ÷ mile/hour = hour``). The quantity unit MUST be the
    rate's numerator, else REFUSE (``dollar ÷ mile/hour``)."""
    if quantity.name != rate.numerator:
        raise UnitError(f"{quantity.name} ÷ {rate}: the quantity unit must be {rate.numerator!r}")
    return BaseUnit(rate.denominator)


__all__ = [
    "BaseUnit",
    "RateUnit",
    "UnitError",
    "rate_from_quantity_over_time",
    "rate_times_time",
    "time_from_quantity_over_rate",
]
