"""Review gate — validate corrections before they become teaching examples.

The reviewer enforces two hard constraints:
  1. Identity override rejected — corrections that attempt to redefine
     CORE's identity axes are blocked.
  2. Bounded — the correction must reference a specific prior turn and
     contain non-empty corrective content.

Reviewed examples carry a deterministic trace (SHA-256 over their content)
so that identical corrections on identical prior turns always produce the
same review hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from teaching.correction import CorrectionCandidate


@unique
class ReviewOutcome(Enum):
    ACCEPTED = "accepted"
    REJECTED_IDENTITY = "rejected_identity"
    REJECTED_EMPTY = "rejected_empty"


_IDENTITY_MARKERS: frozenset[str] = frozenset({
    "you are",
    "your name is",
    "your identity",
    "you must be",
    "you should act as",
    "you are now",
    "forget your",
    "ignore your",
    "override your",
    "your personality",
    "your character",
    "pretend to be",
    "act as if you",
    "from now on you",
})


def _is_identity_override(text: str) -> bool:
    lower = text.lower().strip()
    return any(marker in lower for marker in _IDENTITY_MARKERS)


def _review_hash(candidate: CorrectionCandidate, outcome: ReviewOutcome) -> str:
    payload = json.dumps(
        {
            "candidate_id": candidate.candidate_id,
            "outcome": outcome.value,
            "correction_text": candidate.correction_text,
            "prior_surface": candidate.prior_surface,
            "prior_turn": candidate.prior_turn,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ReviewedTeachingExample:
    candidate: CorrectionCandidate
    outcome: ReviewOutcome
    review_hash: str

    @property
    def accepted(self) -> bool:
        return self.outcome is ReviewOutcome.ACCEPTED

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate": self.candidate.as_dict(),
            "outcome": self.outcome.value,
            "review_hash": self.review_hash,
        }


def review_correction(candidate: CorrectionCandidate) -> ReviewedTeachingExample:
    """Review a correction candidate and produce a teaching example.

    Identity overrides are rejected. Empty corrections are rejected.
    Everything else is accepted.
    """
    if _is_identity_override(candidate.correction_text):
        outcome = ReviewOutcome.REJECTED_IDENTITY
    elif not candidate.correction_text.strip():
        outcome = ReviewOutcome.REJECTED_EMPTY
    else:
        outcome = ReviewOutcome.ACCEPTED

    return ReviewedTeachingExample(
        candidate=candidate,
        outcome=outcome,
        review_hash=_review_hash(candidate, outcome),
    )
