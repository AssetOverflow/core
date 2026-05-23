"""ADR-0131.1 — Symbolic equivalence check (Benchmark 1 primitive).

Given two algebraic expressions A and B, produces an
:class:`EquivalenceVerdict` of EQUIVALENT, NOT_EQUIVALENT, or REFUSED
(with reason). REFUSED preserves wrong == 0: the engine refuses to
guess on out-of-scope input rather than emit a wrong verdict.

Algorithm (v1, polynomial scope):
  1. Normalize A via :func:`generate.math_symbolic_normalizer.normalize`.
  2. Normalize B via the same function.
  3. Compare canonical strings byte-for-byte.

If either normalization raises :class:`SymbolicError`, the verdict is
REFUSED with the propagating reason. This is the wrong-answer
firewall for the benchmark — anything the normalizer cannot prove
equivalent (or prove distinct) deterministically is refused.
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
    canonical_a: str | None  # None when verdict is REFUSED and a couldn't normalize
    canonical_b: str | None
    reason: str  # empty on EQUIVALENT / NOT_EQUIVALENT; non-empty on REFUSED


REFUSED_VERDICTS: Final[frozenset[Verdict]] = frozenset({Verdict.REFUSED})
"""Helper set for callers that need to gate on refusal vs decision."""


def check_equivalence(
    expression_a: str,
    expression_b: str,
    *,
    variable: str = "x",
) -> EquivalenceVerdict:
    """Return whether ``expression_a`` and ``expression_b`` are
    algebraically equivalent under the v1 polynomial-normalizer scope.

    Refusal cases (each surfaces a typed reason):
      - Either expression is empty or non-string.
      - Either expression uses an out-of-scope identifier (multi-
        variable, undefined name).
      - Either expression contains a syntactically invalid construct.
      - Either expression uses division, transcendental functions,
        non-integer coefficients, negative exponents, or non-constant
        exponents.
    """
    try:
        canon_a = normalize(expression_a, variable=variable).to_canonical_string()
    except SymbolicError as exc:
        return EquivalenceVerdict(
            verdict=Verdict.REFUSED,
            canonical_a=None,
            canonical_b=None,
            reason=f"normalize(a) refused: {exc}",
        )

    try:
        canon_b = normalize(expression_b, variable=variable).to_canonical_string()
    except SymbolicError as exc:
        return EquivalenceVerdict(
            verdict=Verdict.REFUSED,
            canonical_a=canon_a,
            canonical_b=None,
            reason=f"normalize(b) refused: {exc}",
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
