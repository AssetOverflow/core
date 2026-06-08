"""Span-free canonical signature for the R3 rate setup oracle (R3b).

A deterministic, order-independent projection of a single-rate setup — the rate unit, the known
values keyed by role, and the query — used to compare a reader's comprehended ``RateProblem``
against the independent gold. The R3 twin of ``evals.setup_oracle.signature`` /
``evals.constraint_oracle.signature``. Pure, deterministic.
"""

from __future__ import annotations

from typing import Any

from generate.rate_comprehension.model import RateProblem


def rate_setup_signature(problem: RateProblem) -> dict[str, Any]:
    """Canonical ``(rate_unit, knowns, query)`` signature of a single-rate setup."""
    knowns = tuple(
        sorted(
            (role, value)
            for role, value in (
                ("rate", problem.rate),
                ("time", problem.time),
                ("quantity", problem.quantity),
            )
            if value is not None
        )
    )
    return {
        "rate_unit": (problem.rate_unit.numerator, problem.rate_unit.denominator),
        "knowns": knowns,
        "query": problem.query,
    }


__all__ = ["rate_setup_signature"]
