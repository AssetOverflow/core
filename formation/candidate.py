"""Candidate dataclasses + ``CandidateState`` lifecycle for the Forge.

A candidate's lifecycle inside the Forge is:

    PROPOSED  -- candidate just out of the Smelter; untrusted.
    QUARANTINED -- failed a Forge rule; retained for audit, not promoted.
    VALIDATED -- passed every Forge rule; emitted with
                 ``EpistemicStatus.SPECULATIVE`` into a ``ValidatedTripleSet``.

This is deliberately disjoint from ``teaching.epistemic.EpistemicStatus``.
``EpistemicStatus`` is a position in the reviewed-revision graph; it does not
include an "unverified" pre-state.  ``CandidateState`` lives entirely
upstream of that enum — once a candidate is ``VALIDATED`` it crosses the
trust boundary and acquires ``EpistemicStatus.SPECULATIVE``.  See ADR-0021.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique


@unique
class CandidateState(Enum):
    """Lifecycle position of a candidate inside the Forge."""

    PROPOSED = "proposed"
    QUARANTINED = "quarantined"
    VALIDATED = "validated"


@dataclass(frozen=True, slots=True)
class SourceRef:
    """Pointer to the source span that produced a candidate.

    ``source_sha`` is the SHA-256 of the source bundle entry (a URL+bytes
    pair captured at mining time).  ``span`` is a quoted excerpt so a human
    reviewer can verify attribution without re-fetching.  ``adapter`` names
    the adapter that produced the candidate (e.g. ``"wikipedia"``,
    ``"user_documents"``, ``"llm_ideation/claude-opus-4-7"``).
    """

    source_sha: str
    span: str
    adapter: str
    retrieved_at: str  # ISO-8601 UTC string; floats forbidden in canonical JSON


@dataclass(frozen=True, slots=True)
class ConceptCandidate:
    """A canonical term with a definition and >=1 source citation."""

    canonical_term: str
    definition: str
    sources: tuple[SourceRef, ...]
    state: CandidateState = CandidateState.PROPOSED
    rejection_reason: str = ""


@dataclass(frozen=True, slots=True)
class RelationCandidate:
    """A typed (head, relation, tail) triple with source attribution."""

    head: str
    relation: str
    tail: str
    sources: tuple[SourceRef, ...]
    state: CandidateState = CandidateState.PROPOSED
    rejection_reason: str = ""


@dataclass(frozen=True, slots=True)
class CounterCandidate:
    """A claim labelled false-but-plausible, mined from errata/corrections."""

    head: str
    relation: str
    tail: str
    sources: tuple[SourceRef, ...]
    state: CandidateState = CandidateState.PROPOSED
    rejection_reason: str = ""


@dataclass(frozen=True, slots=True)
class OrderingHint:
    """Prerequisite signal between two concepts.

    Mined from textbook chapter ordering, paper dependency graphs, etc.
    ``before`` should be introduced prior to ``after`` during Phase III
    walks.
    """

    before: str
    after: str
    sources: tuple[SourceRef, ...] = field(default_factory=tuple)
