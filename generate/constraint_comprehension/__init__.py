"""R2 finite-integer linear-constraint comprehension organ (off-serving).

A parallel typed organ — the R2 twin of the R1 quantitative-comprehension reader. It
compiles two-category constraint word problems (buses/seats, chickens/legs, tickets/prices)
into a typed :class:`ConstraintProblem` graded by an independent setup oracle and solved by
an independent integer solver. Disjoint from the GSM8K serving path (imports no
``generate.derivation`` / ``core.reliability_gate``), so it cannot regress the serving metric.

C1 ships the IR only (this package's ``expr`` + ``model``); the gold/oracle (C2), the
integer solver (C3), the answer-choice verifier (C4), and the reader (C5+) land on top.
"""

from __future__ import annotations

from generate.constraint_comprehension.expr import (
    LinearConstraint,
    LinearExpr,
    Relation,
)
from generate.constraint_comprehension.model import (
    AttributeFact,
    ConstraintProblem,
    ConstraintQuery,
    Domain,
    Unknown,
)
from generate.constraint_comprehension.solver import (
    answer_constraint_problem,
    solve_constraint_problem,
    solve_two_var_count_weight,
    solve_two_var_linear,
)

__all__ = [
    "AttributeFact",
    "ConstraintProblem",
    "ConstraintQuery",
    "Domain",
    "LinearConstraint",
    "LinearExpr",
    "Relation",
    "Unknown",
    "answer_constraint_problem",
    "solve_constraint_problem",
    "solve_two_var_count_weight",
    "solve_two_var_linear",
]
