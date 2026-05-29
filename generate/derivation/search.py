"""ADR-0175 Phase 3b — bounded, deterministic multiplicative derivation search.

The first attempt generator. Conservative by design: it proposes a single
candidate — the **full product of all extracted quantities** — and only when a
multiplicative-relation cue lexeme is present in the text. The proposal is then
passed through the Phase 3a self-verification gate (grounding ∧ unit ∧ unique),
so nothing ungrounded can resolve.

The cue set is an explicit **provisional hypothesis**: it is the search's first
guess at which lexemes license multiplication. It is *not* claimed correct — the
sealed practice lane checks every attempt against gold, and wrong attempts become
elimination records (§9) that refine the hypothesis over time. That refinement is
the compounding loop; this module only stands up the first, gated attempt.

wrong=0 posture: the search runs only in the sealed practice lane (never serving),
every proposal is gated by self-verification, and a non-unique or ungrounded
proposal refuses. Bounded by :data:`MAX_QUANTITIES` (refuse rather than enumerate
an unbounded product).
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Step
from generate.derivation.verify import Resolution, select_self_verified
from generate.math_roundtrip import _tokens

# Provisional multiplicative-cue lexemes (the search's first hypothesis; refined
# by practice elimination, not asserted correct). Sorted use for determinism.
MULTIPLICATIVE_CUES: Final[tuple[str, ...]] = ("each", "every", "for", "per", "times")
MAX_QUANTITIES: Final[int] = 6

_SENTENCE_SPLIT: Final[re.Pattern[str]] = re.compile(r"(?<=[.?!])\s+")


def _sentence_candidates(problem_text: str) -> list[GroundedDerivation]:
    """One in-clause product candidate per sentence that has ≥2 quantities and a
    present multiplicative cue.

    Per-sentence (in-clause) scope is deliberate: it targets the multiplicative
    *aggregate* and avoids multiplying quantities that merely co-occur across
    sentences. When two sentences each yield a product, they disagree and the
    uniqueness gate refuses — so the disagreement rule does real safety work
    instead of being trivially satisfied by a single whole-text candidate.
    """
    candidates: list[GroundedDerivation] = []
    for sentence in _SENTENCE_SPLIT.split(problem_text):
        quantities = extract_quantities(sentence)
        if not 2 <= len(quantities) <= MAX_QUANTITIES:
            continue
        present = [c for c in MULTIPLICATIVE_CUES if c in _tokens(sentence)]
        if not present:
            continue
        cue = present[0]  # deterministic (MULTIPLICATIVE_CUES is sorted-by-design)
        start, *rest = quantities
        candidates.append(
            GroundedDerivation(
                start=start,
                steps=tuple(Step(op="multiply", operand=q, cue=cue) for q in rest),
            )
        )
    return candidates


def multiplicative_candidates(problem_text: str) -> list[GroundedDerivation]:
    """ADR-0182 — the ungated in-clause product candidates, for cross-composer
    pooling. Same construction :func:`search_multiplicative` gates, exposed so the
    pool can weigh products against the other composers' readings."""
    return _sentence_candidates(problem_text)


def search_multiplicative(problem_text: str) -> Resolution | None:
    """Attempt a grounded in-clause multiplicative product.

    Builds one product candidate per qualifying sentence and runs them through
    the Phase 3a gate: a single self-verifying candidate resolves; zero (no
    grounded product) or several that disagree refuse. Deterministic and bounded.
    """
    return select_self_verified(_sentence_candidates(problem_text), problem_text)
