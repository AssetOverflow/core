"""Exact rational time-unit conversion for R3.2 (single-rate only).

The single new capability of R3.2: a duration whose unit differs from the rate's denominator may be
**converted** when both are known time units (``minute`` ↔ ``hour``), instead of refusing. The
conversion is **exact rational** (``fractions.Fraction``) — never a float, never a decimal:

```text
30 minutes -> Fraction(1, 2) hour
90 minutes -> Fraction(3, 2) hour
2 hours    -> Fraction(120) minute
```

So ``60 mile/hour × 30 minute`` becomes ``60 × 1/2 = 30 mile`` (exact). A non-time / non-convertible
pair (``minute`` ↔ ``mile``) raises ``ConversionError`` and the caller still refuses
``rate_unit_mismatch`` — convertibility is the only thing R3.2 adds.

Deliberately tiny: ONLY ``minute`` ↔ ``hour`` in v1. No length (mile↔km), no currency
(dollar↔cent), no compound conversions, no clock-time intervals. Deterministic.
"""

from __future__ import annotations

from fractions import Fraction


class ConversionError(ValueError):
    """The units are not a known convertible pair — the caller must refuse."""


#: Each known time unit as an exact rational number of the base unit (one hour).
_TIME_IN_HOURS: dict[str, Fraction] = {
    "hour": Fraction(1),
    "minute": Fraction(1, 60),
}


def is_convertible(from_unit: str, to_unit: str) -> bool:
    """Whether a conversion exists — the identity (same unit, any kind) or a known time-unit pair."""
    return from_unit == to_unit or (from_unit in _TIME_IN_HOURS and to_unit in _TIME_IN_HOURS)


def convert_time(value: int, from_unit: str, to_unit: str) -> Fraction:
    """Exact rational conversion of *value* ``from_unit`` into *to_unit*. Identity for the same unit
    (any kind, e.g. ``box``); a known time-unit pair otherwise; refuses anything else."""
    if from_unit == to_unit:
        return Fraction(value)
    if from_unit not in _TIME_IN_HOURS or to_unit not in _TIME_IN_HOURS:
        raise ConversionError(f"no exact conversion {from_unit!r} -> {to_unit!r}")
    return Fraction(value) * _TIME_IN_HOURS[from_unit] / _TIME_IN_HOURS[to_unit]


__all__ = ["ConversionError", "convert_time", "is_convertible"]
