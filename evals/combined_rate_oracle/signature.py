"""Span-free canonical signature for the combined-rate setup oracle (CMB-a).

A deterministic, order-independent projection of a combined-rate setup — the combine mode, the
rate unit, the two rates, the known values keyed by role, and the query — used to compare a
reader's comprehended ``CombinedRateProblem`` against the independent gold. The CMB twin of
``evals.rate_oracle.signature``.

Canonical form respects the algebra: ``sum`` is commutative, so its two rates are **sorted** ("3
and 2 together" and "2 and 3 together" are the same thought); ``difference`` is **not**
commutative (which rate is the drain matters), so its rates keep ``(rate_a, rate_b)`` order. Pure,
deterministic.
"""

from __future__ import annotations

from typing import Any

from generate.combined_rate_comprehension.model import CombinedRateProblem


def combined_rate_setup_signature(problem: CombinedRateProblem) -> dict[str, Any]:
    """Canonical ``(combine_mode, rate_unit, rates, knowns, query)`` signature."""
    rates: tuple[int, int] = (problem.rate_a, problem.rate_b)
    if problem.combine_mode == "sum":
        rates = tuple(sorted(rates))  # type: ignore[assignment]  # commutative -> canonicalize order
    knowns = tuple(
        sorted(
            (role, value)
            for role, value in (("time", problem.time), ("quantity", problem.quantity))
            if value is not None
        )
    )
    return {
        "combine_mode": problem.combine_mode,
        "rate_unit": (problem.rate_unit.numerator, problem.rate_unit.denominator),
        "rates": rates,
        "knowns": knowns,
        "query": problem.query,
        # The duration's unit is part of the setup (forward-compat with conversion); in v1 it is
        # always the rate denominator, but the signature carries it for parity with R3.
        "time_unit": problem.time_unit,
    }


__all__ = ["combined_rate_setup_signature"]
