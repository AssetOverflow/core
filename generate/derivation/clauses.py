"""ADR-0178 GB-1 — clause segmentation + clause-local sub-derivation.

The first slice of the comprehension-guided composer: read the problem one clause
at a time and derive each clause's *local* contribution, before GB-2 combines them
across clauses. The text's clause structure is the guidance that keeps the search
bounded and steers grouping (quantities in a clause tend to combine locally).

Segmentation is lexeme/orthographic (ADR-0165) — sentence-level via terminal
punctuation, not a grammar template. Each clause's local sub-derivation reuses the
MS-3 :func:`search_chain` (a small bounded search over that clause's few
quantities); a single-quantity clause is a leaf; a zero-quantity clause is context.
Refuse-preferring: a clause whose local op is ambiguous resolves to nothing (a
hold), it is not guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from generate.derivation.extract import extract_quantities
from generate.derivation.model import Quantity
from generate.derivation.multistep import search_chain

_SENTENCE_SPLIT: Final[re.Pattern[str]] = re.compile(r"(?<=[.?!])\s+")


@dataclass(frozen=True, slots=True)
class ClauseResult:
    """A clause and its locally-derived contribution.

    ``value`` is the clause's local sub-result (``None`` = unresolved/hold —
    context clause, or an ambiguous multi-quantity clause the local search
    refused). ``resolved`` is ``True`` iff a local value was derived.
    """

    text: str
    quantities: tuple[Quantity, ...]
    value: float | None
    unit: str | None
    resolved: bool


def segment_clauses(problem_text: str) -> tuple[str, ...]:
    """Split a problem into clauses (sentence-level, orthographic). Deterministic."""
    return tuple(s.strip() for s in _SENTENCE_SPLIT.split(problem_text) if s.strip())


def clause_local_results(problem_text: str) -> tuple[ClauseResult, ...]:
    """Derive each clause's local contribution (GB-1). Deterministic.

    - 0 quantities  -> context clause (unresolved).
    - 1 quantity    -> leaf (its value).
    - >= 2          -> bounded local search (:func:`search_chain`); resolves to a
                       local value or holds (unresolved) on ambiguity.
    """
    out: list[ClauseResult] = []
    for clause in segment_clauses(problem_text):
        quantities = extract_quantities(clause)
        if len(quantities) == 0:
            out.append(ClauseResult(clause, (), None, None, False))
        elif len(quantities) == 1:
            q = quantities[0]
            out.append(ClauseResult(clause, quantities, q.value, q.unit, True))
        else:
            res = search_chain(clause)
            if res is None:
                out.append(ClauseResult(clause, quantities, None, None, False))
            else:
                out.append(
                    ClauseResult(clause, quantities, res.answer, res.answer_unit, True)
                )
    return tuple(out)
