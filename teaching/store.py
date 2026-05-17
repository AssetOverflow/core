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
from teaching.epistemic import EpistemicStatus
from teaching.review import ReviewedTeachingExample


@dataclass(frozen=True, slots=True)
class PackMutationProposal:
    """A proposed vocabulary manifold change, not yet applied.

    When the correction text parses into a typed (head, relation, tail)
    triple via ``teaching.relation_parse.parse_triple``, the triple is
    stored alongside the opaque text so the inference operators in
    ``generate.operators`` can walk the typed-relation graph that the
    teaching store represents (ADR-0018).

    `epistemic_status` is set to SPECULATIVE at creation per ADR-0021
    §Schema impact: "transitions to COHERENT / CONTESTED / FALSIFIED
    only via the review path."  It is a *position in the revision
    graph*, not a source-trust tier.  No `final`, `frozen`, `axiom`, or
    `permanent` flag exists or may be added (non-hardening invariant,
    ADR-0021 §2).
    """
    proposal_id: str
    candidate_id: str
    subject: str
    correction_text: str
    prior_surface: str
    applied: bool = False
    triple: tuple[str, str, str] | None = None
    epistemic_status: EpistemicStatus = EpistemicStatus.SPECULATIVE

    def as_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "candidate_id": self.candidate_id,
            "subject": self.subject,
            "correction_text": self.correction_text,
            "prior_surface": self.prior_surface,
            "applied": self.applied,
            "triple": list(self.triple) if self.triple is not None else None,
            "epistemic_status": self.epistemic_status.value,
        }

    def with_status(self, status: EpistemicStatus) -> "PackMutationProposal":
        """Return a new proposal with `epistemic_status` set to `status`.

        Immutable update — never mutates the original.  This is the only
        admissible transition path for a proposal's epistemic status; it
        must be driven by a coherence judgment, not by source authority
        (ADR-0021 §3).
        """
        from dataclasses import replace
        return replace(self, epistemic_status=status)


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

        from teaching.relation_parse import parse_triple

        triple = parse_triple(example.candidate.correction_text)
        proposal = PackMutationProposal(
            proposal_id=_proposal_id(example.candidate),
            candidate_id=example.candidate.candidate_id,
            subject=example.candidate.intent.subject,
            correction_text=example.candidate.correction_text,
            prior_surface=example.candidate.prior_surface,
            triple=triple,
            epistemic_status=example.epistemic_status,
        )
        self._proposals.append(proposal)
        return proposal

    def triples(self) -> tuple[tuple[str, str, str], ...]:
        """Return all typed (head, relation, tail) triples currently stored.

        Filters out proposals that did not parse cleanly.  Order is
        append-order, which is the order corrections were reviewed in.
        This is the substrate that ``generate.operators.transitive_walk``
        walks (ADR-0018).
        """
        return tuple(p.triple for p in self._proposals if p.triple is not None)

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
