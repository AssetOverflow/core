"""Independent exact integer solver for the R2 two-variable linear system.

Solves a two-variable, two-equation integer linear system by **exact Cramer's rule** — no
floats, no nearest-option snapping. The R2 analogue of the relational-metric answer oracle:
an independent decision procedure that consumes the *structured* constraints, never the text.

Refusal-first (the wrong=0 boundary). The four ways a count/weight system has no honest
nonnegative-integer answer each REFUSE with a typed reason, never a guessed value:

- ``indistinguishable_weights`` — the system is singular (``det == 0``): the two equations
  cannot separate the unknowns (e.g. equal per-category coefficients), so no unique solution.
- ``non_integer_solution``      — Cramer's numerator is not divisible by the determinant:
  no integer solution exists; the solver refuses rather than round.
- ``negative_solution``         — a solved value is negative: invalid in the count domain.
- ``verification_failed``       — a defensive re-substitution backstop (an algebraic identity
  for the closed-form Cramer solution, so unreachable while the derivation is correct; retained
  as a structural guard against future edits, NOT claimed as an independently-triggerable gate).

The convenience ``solve_two_var_count_weight`` is the canonical ``x + y = N`` /
``a·x + b·y = T`` specialization; ``solve_constraint_problem`` / ``answer_constraint_problem``
drive it from a typed :class:`ConstraintProblem`. Off-serving: imports no
``generate.derivation`` / ``core.reliability_gate``. Deterministic; no clock, no randomness.
"""

from __future__ import annotations

from generate.constraint_comprehension.expr import LinearConstraint, LinearExpr
from generate.constraint_comprehension.model import ConstraintProblem
from generate.meaning_graph.reader import Refusal


def _coeffs(constraint: LinearConstraint, x: str, y: str) -> tuple[int, int, int]:
    """``(coeff_x, coeff_y, rhs - lhs_constant)`` for ``constraint`` over the variables x, y."""
    cx = cy = 0
    for symbol, coeff in constraint.lhs.terms:
        if symbol == x:
            cx += coeff
        elif symbol == y:
            cy += coeff
    return cx, cy, constraint.rhs - constraint.lhs.constant


def solve_two_var_linear(
    c0: LinearConstraint, c1: LinearConstraint, *, nonnegative: bool = True
) -> dict[str, int] | Refusal:
    """Solve a 2-variable, 2-equation integer system over the SAME two symbols by Cramer's rule.

    Precondition (guaranteed upstream by the C2 setup validator / the reader): both constraints
    are ``eq`` over exactly two shared symbols. Returns ``{symbol: value}`` or a typed
    :class:`Refusal` carrying one of the four solver reasons.
    """
    symbols = sorted({s for c in (c0, c1) for s, _ in c.lhs.terms})
    if len(symbols) != 2:  # contract violation — upstream must guarantee two variables
        raise ValueError(f"solver expects exactly two variables; got {symbols}")
    x, y = symbols
    p, q, r0 = _coeffs(c0, x, y)
    r, s, r1 = _coeffs(c1, x, y)

    det = p * s - q * r
    if det == 0:
        return Refusal("indistinguishable_weights", f"singular system over {x}/{y}")
    num_x = r0 * s - q * r1
    num_y = p * r1 - r0 * r
    if num_x % det != 0 or num_y % det != 0:
        return Refusal("non_integer_solution", f"no integer solution for {x}/{y}")
    vx, vy = num_x // det, num_y // det
    if nonnegative and (vx < 0 or vy < 0):
        return Refusal("negative_solution", f"{x}={vx}, {y}={vy}")
    if p * vx + q * vy != r0 or r * vx + s * vy != r1:  # pragma: no cover - identity backstop
        return Refusal("verification_failed", "solution failed re-substitution")
    return {x: vx, y: vy}


def solve_two_var_count_weight(
    x: str, y: str, total_count: int, x_weight: int, y_weight: int, weighted_total: int
) -> dict[str, int] | Refusal:
    """The canonical specialization: ``x + y = total_count`` and
    ``x_weight·x + y_weight·y = weighted_total``. ``x`` / ``y`` are the symbol names."""
    count = LinearConstraint(LinearExpr(((x, 1), (y, 1))), "eq", total_count)
    weighted = LinearConstraint(LinearExpr(((x, x_weight), (y, y_weight))), "eq", weighted_total)
    return solve_two_var_linear(count, weighted)


def solve_constraint_problem(problem: ConstraintProblem) -> dict[str, int] | Refusal:
    """Solve a two-constraint :class:`ConstraintProblem`'s system (order-independent)."""
    if len(problem.constraints) != 2:  # contract violation — upstream guarantees two
        raise ValueError(f"solver expects exactly two constraints; got {len(problem.constraints)}")
    return solve_two_var_linear(problem.constraints[0], problem.constraints[1])


def answer_constraint_problem(problem: ConstraintProblem) -> int | Refusal:
    """Solve, then project to the asked unknown's value (or propagate the refusal)."""
    solution = solve_constraint_problem(problem)
    if isinstance(solution, Refusal):
        return solution
    if problem.query.symbol not in solution:  # pragma: no cover - query is a category (C2)
        return Refusal("query_target_unsolved", problem.query.symbol)
    return solution[problem.query.symbol]


__all__ = [
    "answer_constraint_problem",
    "solve_constraint_problem",
    "solve_two_var_count_weight",
    "solve_two_var_linear",
]
