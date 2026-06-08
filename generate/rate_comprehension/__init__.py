"""R3 single-rate comprehension organ (off-serving).

A fresh, isolated organ for the R3 capability family: explicit single-rate integer problems with
exact compound-unit composition — ``quantity = rate × time`` and its two inverses. Its new
substrate is the compound-unit algebra (``units``); the gold/oracle/solver/reader build on it the
same disciplined way R2 did. Disjoint from the GSM8K serving path (imports no
``generate.derivation`` / ``core.reliability_gate``), so it cannot regress the serving metric.

R3 v1 supports ONLY single-rate problems — no combined rates, no temporal state, no unit
conversion, no multi-equation systems. Those are later R3 slices.
"""

from __future__ import annotations

from generate.rate_comprehension.model import RateProblem, RateRole
from generate.rate_comprehension.reader import read_rate_problem
from generate.rate_comprehension.solver import answer_unit, solve_rate
from generate.rate_comprehension.units import (
    BaseUnit,
    RateUnit,
    UnitError,
    rate_from_quantity_over_time,
    rate_times_time,
    time_from_quantity_over_rate,
)

__all__ = [
    "BaseUnit",
    "RateProblem",
    "RateRole",
    "RateUnit",
    "UnitError",
    "answer_unit",
    "rate_from_quantity_over_time",
    "rate_times_time",
    "read_rate_problem",
    "solve_rate",
    "time_from_quantity_over_rate",
]
