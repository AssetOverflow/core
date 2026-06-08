"""Tests for the exact integer single-rate solver (R3c).

Ties the solver to the R3 gold: every ``solved`` fixture computes its ``gold``; every
``solver_refuses`` fixture refuses with the gold-claimed reason. Exact-or-refuse, never rounds.
"""

from __future__ import annotations

from evals.rate_oracle.runner import _load_rate_gold, gold_to_problem
from generate.meaning_graph.reader import Refusal
from generate.rate_comprehension.model import RateProblem
from generate.rate_comprehension.solver import answer_unit, solve_rate
from generate.rate_comprehension.units import RateUnit


def test_solver_solves_every_solved_fixture() -> None:
    for fx in (f for f in _load_rate_gold() if f["expect"] == "solved"):
        assert solve_rate(gold_to_problem(fx)) == fx["gold"], fx["id"]


def test_solver_refuses_every_solver_refuse_fixture_with_reason() -> None:
    for fx in (f for f in _load_rate_gold() if f["expect"] == "solver_refuses"):
        out = solve_rate(gold_to_problem(fx))
        assert isinstance(out, Refusal) and out.reason == fx["solver_reason"], fx["id"]


def test_forward_product_is_always_integer() -> None:
    assert solve_rate(RateProblem(RateUnit("mile", "hour"), 7, 9, None, "quantity")) == 63


def test_non_exact_inverse_refuses_never_rounds() -> None:
    # 100 mile ÷ 3 hour = 33.3… → refuse (not 33).
    out = solve_rate(RateProblem(RateUnit("mile", "hour"), None, 3, 100, "rate"))
    assert isinstance(out, Refusal) and out.reason == "non_integer_solution"
    # one less mile is exact → 99 ÷ 3 = 33.
    assert solve_rate(RateProblem(RateUnit("mile", "hour"), None, 3, 99, "rate")) == 33


def test_answer_unit_by_query() -> None:
    rp = lambda q, **kw: RateProblem(RateUnit("mile", "hour"), kw.get("rate"), kw.get("time"), kw.get("quantity"), q)  # noqa: E731
    assert answer_unit(rp("quantity", rate=60, time=3)) == "mile"
    assert answer_unit(rp("time", rate=60, quantity=180)) == "hour"
    assert answer_unit(rp("rate", time=3, quantity=180)) == RateUnit("mile", "hour")
