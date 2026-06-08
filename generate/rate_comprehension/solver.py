"""Exact integer single-rate solver (R3c).

Solves the one unknown of a ``RateProblem`` — ``quantity = rate × time`` and its two inverses —
with **exact integer arithmetic** and a **unit-composition** confirmation:

```text
query quantity:  quantity = rate × time              (always integer)
query rate:      rate = quantity ÷ time              (exact division or REFUSE)
query time:      time = quantity ÷ rate              (exact division or REFUSE)
```

No floats, no rounding. A non-exact inverse REFUSES (``non_integer_solution``) rather than
flooring to a wrong integer — the wrong=0 boundary. The compound-unit composition is confirmed via
the unit algebra (R3a); since a ``RateProblem``'s units are consistent by construction, that check
is defensive (a non-composing unit is caught earlier, at the reader). Off-serving; deterministic.
"""

from __future__ import annotations

from generate.meaning_graph.reader import Refusal
from generate.rate_comprehension.model import RateProblem
from generate.rate_comprehension.units import (
    BaseUnit,
    RateUnit,
    UnitError,
    rate_from_quantity_over_time,
    rate_times_time,
    time_from_quantity_over_rate,
)


def solve_rate(problem: RateProblem) -> int | Refusal:
    """Solve the unknown slot exactly, or refuse a non-integer inverse."""
    ru = problem.rate_unit
    try:
        if problem.query == "quantity":
            rate_times_time(ru, BaseUnit(problem.time_unit))  # confirm mile/hour × hour = mile
            assert problem.rate is not None and problem.time is not None
            return problem.rate * problem.time
        if problem.query == "rate":
            rate_from_quantity_over_time(BaseUnit(problem.quantity_unit), BaseUnit(problem.time_unit))
            assert problem.quantity is not None and problem.time is not None
            if problem.quantity % problem.time != 0:
                return Refusal("non_integer_solution", f"{problem.quantity} ÷ {problem.time} (rate)")
            return problem.quantity // problem.time
        # query == "time"
        time_from_quantity_over_rate(BaseUnit(problem.quantity_unit), ru)
        assert problem.quantity is not None and problem.rate is not None
        if problem.quantity % problem.rate != 0:
            return Refusal("non_integer_solution", f"{problem.quantity} ÷ {problem.rate} (time)")
        return problem.quantity // problem.rate
    except UnitError as exc:  # pragma: no cover - a RateProblem's units compose by construction
        return Refusal("rate_unit_mismatch", str(exc))


def answer_unit(problem: RateProblem) -> str | RateUnit:
    """The unit of the answer to *problem* — a base unit string, or a ``RateUnit`` when asking rate."""
    if problem.query == "quantity":
        return problem.quantity_unit
    if problem.query == "time":
        return problem.time_unit
    return problem.rate_unit


__all__ = ["answer_unit", "solve_rate"]
