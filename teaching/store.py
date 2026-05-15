"""Teaching store — bounded persistence for reviewed teaching examples.

TeachingStore is an append-only, bounded collection of accepted
teaching examples. It emits PackMutationProposal objects rather than
mutating the vocabulary manifold directly — external review is required
before any pack change takes effect.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from teaching.correction import CorrectionCandidate
from teaching.review import ReviewedTeachingExample


@dataclass(frozen=True, slots=True)
class PackMutationProposal:
    """A proposed vocabulary manifold change, not yet applied."""
    proposal_id: str
    candidate_id: str
    subject: str
    correction_text: str
    prior_surface: str
    applied: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "candidate_id": self.candidate_id,
            "subject": self.subject,
            "correction_text": self.correction_text,
            "prior_surface": self.prior_surface,
            "applied": self.applied,
        }


def _proposal_id(candidate: CorrectionCandidate) -> str:
    payload = json.dumps(
        {"candidate_id": candidate.candidate_id, "subject": candidate.intent.subject},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class TeachingStore:
    """Bounded, append-only store for reviewed teaching examples.

    Capacity is fixed at construction. When full, the oldest example is
    evicted (FIFO). Only accepted examples are stored; rejected examples
    are silently dropped.
    """

    def __init__(self, capacity: int = 256) -> None:
        self._capacity = capacity
        self._examples: list[ReviewedTeachingExample] = []
        self._proposals: list[PackMutationProposal] = []

    @property
    def capacity(self) -> int:
        return self._capacity

    def add(self, example: ReviewedTeachingExample) -> PackMutationProposal | None:
        """Store an accepted example and return a mutation proposal.

        Rejected examples are dropped silently. Returns None if the
        example was not accepted.
        """
        if not example.accepted:
            return None

        if len(self._examples) >= self._capacity:
            self._examples.pop(0)

        self._examples.append(example)

        proposal = PackMutationProposal(
            proposal_id=_proposal_id(example.candidate),
            candidate_id=example.candidate.candidate_id,
            subject=example.candidate.intent.subject,
            correction_text=example.candidate.correction_text,
            prior_surface=example.candidate.prior_surface,
        )
        self._proposals.append(proposal)
        return proposal

    def retrieve(self, subject: str) -> tuple[ReviewedTeachingExample, ...]:
        """Retrieve all stored examples matching a subject (case-insensitive)."""
        lower = subject.lower()
        return tuple(
            ex for ex in self._examples
            if lower in ex.candidate.intent.subject.lower()
        )

    def pending_proposals(self) -> tuple[PackMutationProposal, ...]:
        """Return all proposals that have not been applied."""
        return tuple(p for p in self._proposals if not p.applied)

    def __len__(self) -> int:
        return len(self._examples)
