"""Exact integer single-rate solver (R3c) with exact-rational unit conversion (R3.2c).

Solves the one unknown of a ``RateProblem`` — ``quantity = rate × time`` and its two inverses —
normalizing the duration to the rate's denominator unit by **exact rational conversion** (R3.2):

```text
query quantity:  quantity = rate × convert(time)                 (exact int or REFUSE)
query rate:      rate = quantity ÷ convert(time)                 (exact int or REFUSE)
query time:      time = quantity ÷ rate  (in the rate denominator unit)  (exact int or REFUSE)
```

``Fraction`` is confined here: ``convert_time`` returns an exact rational, the arithmetic is
exact, and a non-whole result REFUSES (``non_integer_solution``) — **no float, no rounding**. A
duration unit that does not convert to the rate denominator (``…/hour`` for ``3 gallons``) raises
``ConversionError`` and REFUSES (``rate_unit_mismatch``). Off-serving; deterministic.
"""

from __future__ import annotations

from fractions import Fraction

from generate.meaning_graph.reader import Refusal
from generate.rate_comprehension.conversion import ConversionError, convert_time
from generate.rate_comprehension.model import RateProblem
from generate.rate_comprehension.units import RateUnit


def _exact_int(value: Fraction) -> int | Refusal:
    """An exact integer, or a typed refusal — never a rounded/floored approximation."""
    if value.denominator != 1:
        return Refusal("non_integer_solution", str(value))
    return int(value)


def solve_rate(problem: RateProblem) -> int | Refusal:
    """Solve the unknown slot exactly (converting the duration as needed), or refuse."""
    ru = problem.rate_unit
    try:
        if problem.query == "quantity":
            assert problem.rate is not None and problem.time is not None
            time = convert_time(problem.time, problem.time_unit, ru.denominator)
            return _exact_int(Fraction(problem.rate) * time)
        if problem.query == "rate":
            assert problem.quantity is not None and problem.time is not None
            time = convert_time(problem.time, problem.time_unit, ru.denominator)
            return _exact_int(Fraction(problem.quantity) / time)
        # query == "time" — answered in the rate's denominator unit; the duration is the unknown.
        assert problem.quantity is not None and problem.rate is not None
        return _exact_int(Fraction(problem.quantity) / Fraction(problem.rate))
    except ConversionError as exc:
        return Refusal("rate_unit_mismatch", str(exc))


def answer_unit(problem: RateProblem) -> str | RateUnit:
    """The unit of the answer — the rate numerator (quantity), the rate denominator (time), or the
    full ``RateUnit`` (rate)."""
    if problem.query == "quantity":
        return problem.quantity_unit
    if problem.query == "time":
        return problem.rate_unit.denominator
    return problem.rate_unit


__all__ = ["answer_unit", "solve_rate"]
