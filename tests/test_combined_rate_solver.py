"""Tests for the exact combined-rate solver (CMB-b).

Pins wrong=0 for the solver lane: every solved gold setup solves to its gold int; every
solver_refuses setup refuses with its gold reason; the effective_rate query returns the net rate
even when non-positive; non-positive net and non-integer time refuse (never round, never go
negative); and the answer is always an exact int, never a float. Literal-anchored values keep the
solver honest independently of the gold and the oracle's _canonical_outcome.
"""

from __future__ import annotations

from evals.combined_rate_oracle.runner import _load_combined_rate_gold, gold_to_problem, run_solver
from generate.combined_rate_comprehension.model import CombinedRateProblem
from generate.combined_rate_comprehension.solver import solve_combined_rate
from generate.combined_rate_comprehension.units import RateUnit
from generate.meaning_graph.reader import Refusal

_ROOM_HOUR = RateUnit("room", "hour")
_LITER_MIN = RateUnit("liter", "minute")


def _by(expect: str) -> list[dict]:
    return [f for f in _load_combined_rate_gold() if f["expect"] == expect]


def test_solver_lane_is_wrong_zero_and_complete() -> None:
    r = run_solver()
    assert r["solved_wrong"] == 0 and r["refuse_wrong"] == 0
    assert r["solved_correct"] == 6
    assert r["refuse_correct"] == 5
    assert r["skipped_reader_refuses"] == 8


def test_solves_every_solved_fixture_to_gold() -> None:
    for fx in _by("solved"):
        out = solve_combined_rate(gold_to_problem(fx))
        assert out == fx["gold"], f"{fx['id']}: got {out!r}, want {fx['gold']}"


def test_refuses_every_solver_refuse_fixture_with_reason() -> None:
    for fx in _by("solver_refuses"):
        out = solve_combined_rate(gold_to_problem(fx))
        assert isinstance(out, Refusal) and out.reason == fx["solver_reason"], fx["id"]


def test_literal_grid_values() -> None:
    # Hand-computed expected answers — the independent anchor (not gold, not _canonical_outcome).
    assert solve_combined_rate(CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", 4, None, "quantity")) == 20
    assert solve_combined_rate(CombinedRateProblem(5, 2, _LITER_MIN, "difference", 6, None, "quantity")) == 18
    assert solve_combined_rate(CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", None, 20, "time")) == 4
    assert solve_combined_rate(CombinedRateProblem(5, 2, _LITER_MIN, "difference", None, 18, "time")) == 6
    assert solve_combined_rate(CombinedRateProblem(9, 4, _LITER_MIN, "difference", None, None, "effective_rate")) == 5
    assert solve_combined_rate(CombinedRateProblem(6, 4, _LITER_MIN, "sum", None, None, "effective_rate")) == 10


def test_effective_rate_query_returns_net_even_when_nonpositive() -> None:
    # The net rate is a well-defined answer even at/below zero — the effective_rate query never refuses.
    assert solve_combined_rate(CombinedRateProblem(4, 4, _LITER_MIN, "difference", None, None, "effective_rate")) == 0
    assert solve_combined_rate(CombinedRateProblem(2, 5, _LITER_MIN, "difference", None, None, "effective_rate")) == -3


def test_non_positive_net_rate_refuses_quantity_and_time() -> None:
    # Full (eff<=0) x (quantity, time) grid: eff==0/quantity, eff<0/quantity, eff==0/time (would /0),
    # eff<0/time. All inputs positive; only the net rate is non-positive.
    for p in (
        CombinedRateProblem(4, 4, _LITER_MIN, "difference", 5, None, "quantity"),
        CombinedRateProblem(2, 5, _LITER_MIN, "difference", 3, None, "quantity"),
        CombinedRateProblem(4, 4, _LITER_MIN, "difference", None, 12, "time"),
        CombinedRateProblem(2, 5, _LITER_MIN, "difference", None, 9, "time"),
    ):
        out = solve_combined_rate(p)
        assert isinstance(out, Refusal) and out.reason == "non_positive_net_rate"


def test_non_integer_time_refuses() -> None:
    # 12 / (3+2) = 2.4 -> refuse, never round to 2 or 3.
    out = solve_combined_rate(CombinedRateProblem(3, 2, _ROOM_HOUR, "sum", None, 12, "time"))
    assert isinstance(out, Refusal) and out.reason == "non_integer_solution"


def test_quantity_query_is_always_integral() -> None:
    # eff * time is integral for any integer rates/time -> never a non_integer refusal on quantity.
    # Expected values are computed INLINE (not via model.effective_rate) — the real anchor against a
    # shared effective_rate bug — for BOTH sum and difference modes.
    for ra, rb, t in ((3, 2, 7), (5, 2, 9), (1, 1, 100)):
        out = solve_combined_rate(CombinedRateProblem(ra, rb, _ROOM_HOUR, "sum", t, None, "quantity"))
        assert isinstance(out, int) and out == (ra + rb) * t
    for ra, rb, t in ((5, 2, 6), (9, 4, 3), (7, 1, 8)):  # rate_a > rate_b so eff > 0
        out = solve_combined_rate(CombinedRateProblem(ra, rb, _LITER_MIN, "difference", t, None, "quantity"))
        assert isinstance(out, int) and out == (ra - rb) * t


def test_solver_answer_is_int_never_float_or_bool() -> None:
    out = solve_combined_rate(CombinedRateProblem(5, 2, _LITER_MIN, "difference", None, 18, "time"))
    assert type(out) is int  # not float, not bool


def test_solver_module_is_off_serving() -> None:
    import ast
    from pathlib import Path

    import generate.combined_rate_comprehension.solver as solver_mod

    forbidden = ("generate.derivation", "core.reliability_gate")
    for node in ast.walk(ast.parse(Path(str(solver_mod.__file__)).read_text(encoding="utf-8"))):
        names = (
            [a.name for a in node.names] if isinstance(node, ast.Import)
            else [node.module or ""] if isinstance(node, ast.ImportFrom)
            else []
        )
        for name in names:
            assert not any(name.startswith(t) for t in forbidden), f"solver imports {name}"
