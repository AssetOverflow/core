"""End-to-end conversion solving (R3.2c/d) — the extra cases pinned in the R3.2 plan."""

from __future__ import annotations

from fractions import Fraction

from generate.meaning_graph.reader import Refusal
from generate.rate_comprehension.model import RateProblem
from generate.rate_comprehension.reader import read_rate_problem
from generate.rate_comprehension.solver import solve_rate
from generate.rate_comprehension.units import RateUnit

_MPH = RateUnit("mile", "hour")


def test_30_minutes_at_60_mph_is_30_miles() -> None:
    assert solve_rate(RateProblem(_MPH, 60, 30, None, "quantity", time_unit="minute")) == 30


def test_90_minutes_at_60_mph_is_90_miles() -> None:
    assert solve_rate(RateProblem(_MPH, 60, 90, None, "quantity", time_unit="minute")) == 90


def test_45_minutes_at_10_mph_is_non_integer_refused() -> None:
    # 10 mile/hour × 45/60 hour = 15/2 = 7.5 -> REFUSE (never 7 or 8).
    out = solve_rate(RateProblem(_MPH, 10, 45, None, "quantity", time_unit="minute"))
    assert isinstance(out, Refusal) and out.reason == "non_integer_solution"


def test_minutes_rate_needs_no_conversion() -> None:
    # 60 mile/minute for 30 minutes -> identity, 60 × 30 = 1800 mile.
    assert solve_rate(RateProblem(RateUnit("mile", "minute"), 60, 30, None, "quantity", time_unit="minute")) == 1800


def test_non_convertible_duration_refuses_at_reader() -> None:
    out = read_rate_problem("A car travels 60 miles per hour for 3 gallons. How many miles does it travel?")
    assert isinstance(out, Refusal) and out.reason == "rate_unit_mismatch"


def test_convertible_duration_reads_and_solves_end_to_end() -> None:
    problem = read_rate_problem("A car travels 60 miles per hour for 30 minutes. How many miles does it travel?")
    assert not isinstance(problem, Refusal)
    assert problem.time == 30 and problem.time_unit == "minute"  # text-faithful: stored as minutes
    assert solve_rate(problem) == 30


def test_solver_answer_is_int_never_float() -> None:
    result = solve_rate(RateProblem(_MPH, 60, 90, None, "quantity", time_unit="minute"))
    assert isinstance(result, int) and not isinstance(result, (float, Fraction))
