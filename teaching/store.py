"""Teaching store — bounded persistence for reviewed teaching examples.

TeachingStore is an append-only, bounded collection of accepted
teaching examples. It emits PackMutationProposal objects rather than
mutating the vocabulary manifold directly — external review is required
before any pack change takes effect.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from teaching.correction import CorrectionCandidate
from teaching.epistemic import EpistemicStatus
from teaching.review import ReviewedTeachingExample
from teaching.source import ProposalSource


# ADR-0021 §CONTESTED transitions: coherence checker tokens.
# Negation markers and opposition markers used to detect (S, R, T) ↔
# (S, R, ¬T) pairs at add() time.
_NEGATION_TOKENS: frozenset[str] = frozenset({
    "not", "no", "isn't", "aren't", "wasn't", "weren't",
    "never", "without", "neither", "nor",
})
_OPPOSITION_MARKERS: frozenset[str] = frozenset({
    "unrelated", "independent", "opposite", "contrary",
    "incompatible", "disjoint",
})
_STOPWORDS: frozenset[str] = frozenset({
    "the", "and", "but", "for", "with", "from", "into", "onto",
    "this", "that", "these", "those", "are", "was", "were",
    "has", "had", "have", "been", "being",
})
# Discourse/teaching markers that appear in correction texts but carry no
# semantic content — excluded from shared-content overlap so they don't
# inflate the contradiction signal between unrelated corrections.
_DISCOURSE_MARKERS: frozenset[str] = frozenset({
    "actually", "correction", "indeed", "rather", "instead", "really",
})
_WORD_SPLIT = re.compile(r"[^a-z]+")


def _content_tokens(text: str) -> set[str]:
    """≥3-char tokens minus stopwords AND discourse markers — used for
    shared-content overlap.  Discourse markers ("actually", "correction",
    …) are excluded so they don't inflate the contradiction signal."""
    return {
        tok for tok in _WORD_SPLIT.split(text.lower())
        if len(tok) >= 3
        and tok not in _STOPWORDS
        and tok not in _DISCOURSE_MARKERS
    }


def _subject_tokens(proposal: PackMutationProposal) -> set[str]:
    """Extract candidate subject content tokens from raw subject and
    parsed-triple subject.  Used as a lenient match key for contradiction
    detection so "meaning" matches both ", meaning depends on use." and
    "meaning" (parsed-triple head)."""
    sources: list[str] = [proposal.subject]
    if proposal.triple is not None and proposal.triple[0]:
        sources.append(proposal.triple[0])
    tokens: set[str] = set()
    for src in sources:
        tokens |= _content_tokens(src)
    return tokens


def _has_negation(text: str) -> bool:
    """Detect surface negation or opposition tokens."""
    tokens = set(_WORD_SPLIT.split(text.lower()))
    return bool(tokens & _NEGATION_TOKENS) or bool(tokens & _OPPOSITION_MARKERS)


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
    source: ProposalSource
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
            "source": self.source.as_dict(),
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

        ADR-0021 §CONTESTED transitions: before appending, the new
        proposal is checked against prior proposals for direct
        contradiction (same subject, conflicting polarity).  When a
        contradiction is detected, BOTH the new proposal and the
        conflicting prior are upgraded to ``EpistemicStatus.CONTESTED``
        — neither is admissible as evidence until a coherence judgment
        ratifies one of them.  See ``_detect_contradiction``.
        """
        if not example.accepted:
            return None

        if len(self._examples) >= self._capacity:
            self._examples.pop(0)

        self._examples.append(example)

        from teaching.relation_parse import parse_triple

        triple = parse_triple(example.candidate.correction_text)
        # ADR-0094: PackMutationProposals built from reviewed teaching
        # examples are operator-authored; miner-sourced and curriculum-
        # sourced construction sites land in ADR-0095 and later.
        from teaching.proposals import _default_operator_source
        proposal = PackMutationProposal(
            proposal_id=_proposal_id(example.candidate),
            candidate_id=example.candidate.candidate_id,
            subject=example.candidate.intent.subject,
            correction_text=example.candidate.correction_text,
            prior_surface=example.candidate.prior_surface,
            source=_default_operator_source(),
            triple=triple,
            epistemic_status=example.epistemic_status,
        )

        # Coherence judgment — detect (S, R, T) ↔ (S, R, ¬T) pairs and
        # transition both proposals to CONTESTED.  ADR-0021: CONTESTED is
        # not admissible as evidence; the next reviewed correction can
        # ratify one direction back to COHERENT or FALSIFY the other.
        conflict_idx = self._detect_contradiction(proposal)
        if conflict_idx is not None:
            proposal = proposal.with_status(EpistemicStatus.CONTESTED)
            self._proposals[conflict_idx] = self._proposals[conflict_idx].with_status(
                EpistemicStatus.CONTESTED
            )

        self._proposals.append(proposal)
        return proposal

    def _detect_contradiction(
        self, new_proposal: PackMutationProposal
    ) -> int | None:
        """Return the index of a prior proposal that contradicts ``new_proposal``,
        or None.

        Detection has two paths.  Both require subject identity after
        stripping discourse prefixes (so "correction: knowledge" matches
        "knowledge").

        Path A — typed: both proposals parsed to triples with the same
        relation.  Tails must differ in negation polarity AND share at
        least one content token.  Catches the clean
        (S, R, T) ↔ (S, R, not T) shape.

        Path B — text fallback: at least one proposal failed to parse a
        triple (e.g. the relation predicate isn't in the cognition pack
        lexicon yet, like "depends").  Correction texts must differ in
        negation polarity AND share at least one non-subject content
        token.  Catches paraphrased contradictions like "X depends on Y"
        vs "X is independent of Y".

        Returns the index of the first matching prior in
        ``self._proposals``, or None if no contradiction is found.
        Existing CONTESTED proposals are skipped — once contested,
        further contradictions don't add information until review.
        """
        new_subjects = _subject_tokens(new_proposal)
        if not new_subjects:
            return None
        new_text_negated = _has_negation(new_proposal.correction_text)
        new_text_tokens = _content_tokens(new_proposal.correction_text)

        for idx, prior in enumerate(self._proposals):
            if prior.epistemic_status is EpistemicStatus.CONTESTED:
                continue
            prior_subjects = _subject_tokens(prior)
            if not (new_subjects & prior_subjects):
                continue

            # Path A — typed: both parsed AND same relation.  Tails must
            # differ in polarity and share at least one content token.
            if (
                new_proposal.triple is not None
                and prior.triple is not None
                and new_proposal.triple[1] == prior.triple[1]
            ):
                new_tail = new_proposal.triple[2]
                prior_tail = prior.triple[2]
                if _has_negation(new_tail) != _has_negation(prior_tail):
                    if _content_tokens(new_tail) & _content_tokens(prior_tail):
                        return idx

            # Path B — text fallback.  At least one proposal failed to
            # parse a triple (or relations differ).  Polarity must differ
            # and the texts must share ≥2 non-subject content tokens —
            # the ≥2 threshold prevents a single shared subject token from
            # flagging unrelated corrections as contradictions.
            prior_text_negated = _has_negation(prior.correction_text)
            if new_text_negated != prior_text_negated:
                prior_text_tokens = _content_tokens(prior.correction_text)
                shared = new_text_tokens & prior_text_tokens
                if len(shared) >= 2:
                    return idx

        return None

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
