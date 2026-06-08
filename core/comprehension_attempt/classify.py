"""Normalize R1/R2 organ output into a typed ``ComprehensionAttempt`` (N2, setup-level).

`classify_r1` / `classify_r2` run their organ and report **produce-mode** setup outcomes:
`setup_refused` (with the organ's typed reason) or `setup_correct` (an admissible setup was
produced, with a deterministic signature). They do NOT solve, do NOT compare to gold, and import
nothing from `evals` (signatures are computed inline) — keeping this a thin, dependency-light
normalizer. Answer-level outcomes are reached downstream (N6) when the solver/verifier run.
"""

from __future__ import annotations

from typing import Any

from core.comprehension_attempt.model import ComprehensionAttempt
from generate.constraint_comprehension.model import ConstraintProblem
from generate.constraint_comprehension.reader import read_constraint_problem
from generate.meaning_graph.reader import Refusal
from generate.quantitative_comprehension import comprehend_quantitative, to_relational_metric
from generate.rate_comprehension.model import RateProblem
from generate.rate_comprehension.reader import read_rate_problem


def _r1_signature(relations: list[dict[str, Any]]) -> str:
    """Deterministic, order-independent string signature of the projected R1 relations."""
    items: list[tuple] = []
    for r in relations:
        kind = r["kind"]
        if kind == "fact":
            items.append((kind, r["entity"], int(r["value"])))
        elif kind in ("more_than", "fewer_than"):
            items.append((kind, r["entity"], r["ref"], int(r["delta"])))
        elif kind == "times_as_many":
            items.append((kind, r["entity"], r["ref"], int(r["factor"])))
        elif kind == "divide_by":
            items.append((kind, r["entity"], r["ref"], int(r["divisor"])))
        elif kind == "sum_of":
            items.append((kind, r["entity"], tuple(sorted(r["parts"]))))
        else:  # pragma: no cover - defensive
            items.append(("unhandled", kind, r.get("entity", "")))
    return repr(tuple(sorted(items, key=repr)))


def _r2_signature(problem: ConstraintProblem) -> str:
    """Deterministic, order-independent string signature of an R2 ConstraintProblem setup."""
    unknowns = tuple(sorted((u.symbol, u.unit, u.domain) for u in problem.unknowns))
    constraints: list[tuple] = []
    for c in problem.constraints:
        merged: dict[str, int] = {}
        for symbol, coeff in c.lhs.terms:
            merged[symbol] = merged.get(symbol, 0) + coeff
        terms = tuple(sorted((s, v) for s, v in merged.items() if v != 0))
        constraints.append((terms, c.relation, c.rhs - c.lhs.constant))
    query = (problem.query.symbol, problem.query.unit)
    return repr((unknowns, tuple(sorted(constraints, key=repr)), query))


def classify_r1(text: str, *, case_id: str | None = None) -> ComprehensionAttempt:
    """Attempt the R1 relational-arithmetic setup compiler on *text*."""
    comp = comprehend_quantitative(text)
    if isinstance(comp, Refusal):
        return ComprehensionAttempt(
            "r1_quantitative", "setup_refused", case_id=case_id, refusal_reason=comp.reason
        )
    projected = to_relational_metric(comp)
    if projected is None:
        return ComprehensionAttempt(
            "r1_quantitative", "setup_refused", case_id=case_id, refusal_reason="unprojectable"
        )
    relations, _query = projected
    return ComprehensionAttempt(
        "r1_quantitative", "setup_correct", case_id=case_id, setup_signature=_r1_signature(relations)
    )


def classify_r2(text: str, *, case_id: str | None = None) -> ComprehensionAttempt:
    """Attempt the R2 two-category constraint setup compiler on *text*."""
    problem = read_constraint_problem(text)
    if isinstance(problem, Refusal):
        return ComprehensionAttempt(
            "r2_constraints", "setup_refused", case_id=case_id, refusal_reason=problem.reason
        )
    return ComprehensionAttempt(
        "r2_constraints", "setup_correct", case_id=case_id, setup_signature=_r2_signature(problem)
    )


def _r3_signature(problem: RateProblem) -> str:
    """Deterministic string signature of an R3 single-rate setup."""
    return repr(
        (
            (problem.rate_unit.numerator, problem.rate_unit.denominator),
            ("rate", problem.rate),
            ("time", problem.time),
            ("quantity", problem.quantity),
            problem.query,
        )
    )


def classify_r3(text: str, *, case_id: str | None = None) -> ComprehensionAttempt:
    """Attempt the R3 single-rate setup compiler on *text*."""
    problem = read_rate_problem(text)
    if isinstance(problem, Refusal):
        return ComprehensionAttempt(
            "r3_rate", "setup_refused", case_id=case_id, refusal_reason=problem.reason
        )
    return ComprehensionAttempt(
        "r3_rate", "setup_correct", case_id=case_id, setup_signature=_r3_signature(problem)
    )


__all__ = ["classify_r1", "classify_r2", "classify_r3"]
