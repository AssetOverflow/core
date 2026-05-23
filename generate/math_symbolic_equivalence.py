"""ADR-0131.1.B — Symbolic equivalence check.

Given two algebraic expressions A and B, produces an
:class:`EquivalenceVerdict` of EQUIVALENT, NOT_EQUIVALENT, or REFUSED.
REFUSED preserves wrong == 0: the engine refuses to guess on
out-of-scope input rather than emit a wrong verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from generate.math_symbolic_normalizer import (
    SymbolicError,
    normalize,
)


class Verdict(str, Enum):
    EQUIVALENT = "equivalent"
    NOT_EQUIVALENT = "not_equivalent"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class EquivalenceVerdict:
    verdict: Verdict
    canonical_a: str | None
    canonical_b: str | None
    reason: str


REFUSED_VERDICTS: Final[frozenset[Verdict]] = frozenset({Verdict.REFUSED})
"""Helper set for callers that need to gate on refusal vs decision."""


def _normalize_pair(
    expression_a: str,
    expression_b: str,
    *,
    variable: str | None,
    variables: tuple[str, ...] | None,
) -> tuple[str, str]:
    if variables is None and variable is None:
        # Infer variables from the union of both expressions so `x + y` and
        # `y + x` normalize in the same variable space.
        poly_a_probe = normalize(expression_a)
        poly_b_probe = normalize(expression_b)
        variables = tuple(sorted(set(poly_a_probe.variables) | set(poly_b_probe.variables)))
    canon_a = normalize(expression_a, variable=variable, variables=variables).to_canonical_string()
    canon_b = normalize(expression_b, variable=variable, variables=variables).to_canonical_string()
    return canon_a, canon_b


def check_equivalence(
    expression_a: str,
    expression_b: str,
    *,
    variable: str | None = None,
    variables: tuple[str, ...] | None = None,
) -> EquivalenceVerdict:
    """Return whether two expressions are algebraically equivalent.

    ``variable`` is retained for backward compatibility with the v1
    univariate API. New callers can omit it and allow variable inference, or
    pass an explicit sorted ``variables`` tuple.
    """
    try:
        canon_a, canon_b = _normalize_pair(
            expression_a,
            expression_b,
            variable=variable,
            variables=variables,
        )
    except SymbolicError as exc:
        return EquivalenceVerdict(
            verdict=Verdict.REFUSED,
            canonical_a=None,
            canonical_b=None,
            reason=f"normalize refused: {exc}",
        )

    if canon_a == canon_b:
        return EquivalenceVerdict(
            verdict=Verdict.EQUIVALENT,
            canonical_a=canon_a,
            canonical_b=canon_b,
            reason="",
        )
    return EquivalenceVerdict(
        verdict=Verdict.NOT_EQUIVALENT,
        canonical_a=canon_a,
        canonical_b=canon_b,
        reason="",
    )
