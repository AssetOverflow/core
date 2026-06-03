"""ADR-0201 — Propositional equivalence check.

Boolean-logic twin of :mod:`generate.math_symbolic_equivalence`. Given two
propositional formulas A and B, produces an :class:`EquivalenceVerdict` of
EQUIVALENT, NOT_EQUIVALENT, or REFUSED, by canonicalizing each to its ROBDD
identity (:mod:`generate.logic_canonical`) and comparing the canonical keys by
byte-equality.

REFUSED preserves ``wrong == 0``: out-of-grammar input or a diagram that exceeds
the node budget refuses rather than emitting a verdict — the same posture as the
algebra sibling refusing on out-of-scope expressions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from generate.logic_canonical import (
    DEFAULT_MAX_NODES,
    OUT_OF_DECIDABLE_REGIME,
    LogicBudgetError,
    LogicError,
    LogicRegimeError,
    canonicalize,
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


def check_equivalence(
    formula_a: str,
    formula_b: str,
    *,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> EquivalenceVerdict:
    """Return whether two propositional formulas are logically equivalent.

    Equivalence is decided by ROBDD canonical-key byte-equality, which is exact
    for propositional logic. Refuses (rather than guesses) on malformed input or
    on diagram blowup beyond ``max_nodes``.
    """
    try:
        canon_a = canonicalize(formula_a, max_nodes=max_nodes).canonical_key
        canon_b = canonicalize(formula_b, max_nodes=max_nodes).canonical_key
    except LogicBudgetError as exc:
        return EquivalenceVerdict(
            verdict=Verdict.REFUSED,
            canonical_a=None,
            canonical_b=None,
            reason=f"canonicalization_budget_exceeded: {exc}",
        )
    except LogicRegimeError as exc:
        # Out of the decidable propositional regime (quantified/predicate).
        # Caught before the generic LogicError branch since it is a subclass.
        return EquivalenceVerdict(
            verdict=Verdict.REFUSED,
            canonical_a=None,
            canonical_b=None,
            reason=f"{OUT_OF_DECIDABLE_REGIME}: {exc}",
        )
    except LogicError as exc:
        return EquivalenceVerdict(
            verdict=Verdict.REFUSED,
            canonical_a=None,
            canonical_b=None,
            reason=f"canonicalize refused: {exc}",
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
