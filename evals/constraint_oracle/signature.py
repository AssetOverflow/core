"""Span-free canonical signatures for the R2 constraint setup oracle.

A *signature* is a deterministic, order-independent, span-free projection of a constraint
SETUP — what a reader claims a problem says, stripped of input spans and surface tokens. Two
setups are equivalent iff their signatures are equal. Used to compare a reader's comprehended
:class:`ConstraintProblem` against the independent gold (and, until the reader lands in C5+,
to prove the gold itself canonicalizes stably).

The R2 twin of ``evals.setup_oracle.signature``. Pure, deterministic; no clock, no randomness.
"""

from __future__ import annotations

from typing import Any

from generate.constraint_comprehension.expr import LinearConstraint, LinearExpr
from generate.constraint_comprehension.model import (
    AttributeFact,
    ConstraintProblem,
    ConstraintQuery,
    Unknown,
)


def canonical_linear(expr: LinearExpr) -> tuple[tuple[tuple[str, int], ...], int]:
    """Merge duplicate symbols, drop zero coefficients, sort by symbol -> ``(terms, constant)``."""
    merged: dict[str, int] = {}
    for symbol, coeff in expr.terms:
        merged[symbol] = merged.get(symbol, 0) + coeff
    terms = tuple(sorted((s, c) for s, c in merged.items() if c != 0))
    return terms, expr.constant


def canonical_constraint(c: LinearConstraint) -> tuple[tuple[tuple[str, int], ...], str, int]:
    """A span-free canonical equation: ``(merged sorted lhs terms, relation, rhs - lhs constant)``.

    Folding the lhs constant into the rhs makes ``x + y + 0 = 6`` and ``x + y = 6`` equal; the
    source span never participates — two constraints are setup-equal iff lhs/relation/rhs match.
    """
    terms, constant = canonical_linear(c.lhs)
    return terms, c.relation, c.rhs - constant


def unknowns_signature(unknowns: tuple[Unknown, ...]) -> tuple[tuple[str, str, str], ...]:
    """Sorted ``(symbol, unit, domain)`` per unknown — surface ``entity`` is provenance, excluded."""
    return tuple(sorted((u.symbol, u.unit, u.domain) for u in unknowns))


def constraints_signature(
    constraints: tuple[LinearConstraint, ...],
) -> tuple[tuple[tuple[tuple[str, int], ...], str, int], ...]:
    """Order-independent canonical signature of the whole linear system."""
    return tuple(sorted((canonical_constraint(c) for c in constraints), key=repr))


def query_signature(query: ConstraintQuery) -> tuple[str, str]:
    return (query.symbol, query.unit)


def attribute_facts_signature(
    facts: tuple[AttributeFact, ...],
) -> tuple[tuple[str, str, int], ...]:
    """Sorted ``(category, measured_unit, value)`` — the per-category coefficient provenance."""
    return tuple(sorted((f.category, f.measured_unit, f.value) for f in facts))


def constraint_setup_signature(problem: ConstraintProblem) -> dict[str, Any]:
    """The composite setup signature: unknowns ∧ facts ∧ constraints ∧ query.

    A reader matches gold iff every component is equal. Returned as a dict so a mismatch
    localizes which axis diverged (mirroring the R1 setup oracle's per-axis ``*_match`` detail).
    """
    return {
        "unknowns": unknowns_signature(problem.unknowns),
        "facts": attribute_facts_signature(problem.facts),
        "constraints": constraints_signature(problem.constraints),
        "query": query_signature(problem.query),
    }


__all__ = [
    "attribute_facts_signature",
    "canonical_constraint",
    "canonical_linear",
    "constraint_setup_signature",
    "constraints_signature",
    "query_signature",
    "unknowns_signature",
]
