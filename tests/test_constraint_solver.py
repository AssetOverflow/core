"""Tests for the R2 exact integer solver (C3).

Ties the solver to the C2 gold: every ``solved`` fixture computes its ``gold`` and every
``solver_refuses`` fixture refuses with EXACTLY the reason the gold claims (so the gold's
stated refusal reason is not just an annotation — the independent solver agrees). Each of the
three reachable refusals is proven meaningful-fail, and every solution is re-substituted into
its constraints (the verification backstop, exercised positively).
"""

from __future__ import annotations

from evals.constraint_oracle.runner import _load_r2_gold, gold_to_problem
from evals.constraint_oracle.signature import canonical_constraint
from generate.constraint_comprehension.solver import (
    answer_constraint_problem,
    solve_constraint_problem,
    solve_two_var_count_weight,
    solve_two_var_linear,
)
from generate.meaning_graph.reader import Refusal


def _solved() -> list[dict]:
    return [f for f in _load_r2_gold() if f["expect"] == "solved"]


def _solver_refuses() -> list[dict]:
    return [f for f in _load_r2_gold() if f["expect"] == "solver_refuses"]


def test_solver_solves_every_solved_gold_to_its_gold_value() -> None:
    for fx in _solved():
        problem = gold_to_problem(fx)
        got = answer_constraint_problem(problem)
        assert got == fx["gold"], f"{fx['id']}: got {got!r}, gold {fx['gold']!r}"


def test_solver_solution_satisfies_both_constraints() -> None:
    # The verification backstop, exercised positively: the solved values re-substitute exactly.
    for fx in _solved():
        problem = gold_to_problem(fx)
        sol = solve_constraint_problem(problem)
        assert isinstance(sol, dict), fx["id"]
        for c in problem.constraints:
            terms, _rel, rhs = canonical_constraint(c)
            assert sum(coeff * sol[s] for s, coeff in terms) == rhs


def test_solver_refuses_every_solver_refuse_gold_with_its_claimed_reason() -> None:
    for fx in _solver_refuses():
        problem = gold_to_problem(fx)
        got = answer_constraint_problem(problem)
        assert isinstance(got, Refusal), f"{fx['id']} should refuse"
        assert got.reason == fx["solver_reason"], f"{fx['id']}: {got.reason} != {fx['solver_reason']}"


def test_count_weight_convenience_matches_buses() -> None:
    assert solve_two_var_count_weight("large_bus", "small_bus", 6, 50, 30, 260) == {
        "large_bus": 4,
        "small_bus": 2,
    }


def test_solver_is_constraint_order_independent() -> None:
    fx = next(f for f in _solved() if f["id"] == "r2-002-chickens")
    p = gold_to_problem(fx)
    swapped = solve_two_var_linear(p.constraints[1], p.constraints[0])
    assert swapped == solve_two_var_linear(p.constraints[0], p.constraints[1]) == {"chicken": 11, "cow": 7}


# --- meaningful-fail: each reachable refusal fires under exactly its violation --------- #


def test_indistinguishable_weights_refuses() -> None:
    # Equal coefficients -> singular system -> no unique solution.
    out = solve_two_var_count_weight("car", "truck", 8, 4, 4, 32)
    assert isinstance(out, Refusal) and out.reason == "indistinguishable_weights"


def test_non_integer_solution_refuses() -> None:
    # 3*pen + 5*notebook = 37, pen+notebook=10 -> pen = 6.5: refuse, never round.
    out = solve_two_var_count_weight("pen", "notebook", 10, 3, 5, 37)
    assert isinstance(out, Refusal) and out.reason == "non_integer_solution"


def test_negative_solution_refuses() -> None:
    # 50*large + 30*small = 400, large+small=6 -> small=-5: refuse.
    out = solve_two_var_count_weight("large_bus", "small_bus", 6, 50, 30, 400)
    assert isinstance(out, Refusal) and out.reason == "negative_solution"


def test_exact_integer_path_is_not_rounded() -> None:
    # A near-miss that would round to a plausible integer: 3x+5y=38, x+y=10 -> x=6 exactly.
    # (Guards that the solver computes exactly, not by snapping 37/38/39 to the same answer.)
    assert solve_two_var_count_weight("x", "y", 10, 3, 5, 38) == {"x": 6, "y": 4}
    assert isinstance(
        solve_two_var_count_weight("x", "y", 10, 3, 5, 37), Refusal
    )  # one less dollar -> no integer split
