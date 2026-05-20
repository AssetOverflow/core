"""Typed articulation legality checks at the realizer boundary.

C1.5 scope:
  - Catch a narrow class of known-illegal finite-predicate shapes.
  - Fail open when predicate slot kind is unknown.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SlotKind(Enum):
    VERB = "verb"
    NON_VERB = "non_verb"
    UNKNOWN = "unknown"


class ArticulationLegality(Enum):
    LEGAL = "legal"
    ILLEGAL_NON_VERB_FINITE_PREDICATE = "illegal_non_verb_finite_predicate"


@dataclass(frozen=True, slots=True)
class ArticulationLegalityVerdict:
    legality: ArticulationLegality
    predicate_kind: SlotKind

    @property
    def is_legal(self) -> bool:
        return self.legality is ArticulationLegality.LEGAL


_KNOWN_NON_VERB_PREDICATES: frozenset[str] = frozenset(
    {
        "right",
        "truth",
        "light",
        "knowledge",
        "wisdom",
        "evidence",
        "thought",
        "memory",
    }
)

_KNOWN_VERB_PREDICATES: frozenset[str] = frozenset(
    {
        "is",
        "are",
        "has",
        "have",
        "belongs",
        "supports",
        "requires",
        "grounds",
        "reveals",
        "defines",
        "means",
        "follows",
        "precedes",
        "causes",
        "answers",
        "verifies",
        "evidences",
    }
)


def classify_predicate_slot_kind(predicate_humanized: str) -> SlotKind:
    token = predicate_humanized.strip().split(" ", 1)[0].lower()
    if token in _KNOWN_VERB_PREDICATES:
        return SlotKind.VERB
    if token in _KNOWN_NON_VERB_PREDICATES:
        return SlotKind.NON_VERB
    return SlotKind.UNKNOWN


def validate_finite_predicate_legality(
    *,
    predicate_humanized: str,
    negated: bool,
) -> ArticulationLegalityVerdict:
    kind = classify_predicate_slot_kind(predicate_humanized)
    if not negated:
        return ArticulationLegalityVerdict(
            legality=ArticulationLegality.LEGAL,
            predicate_kind=kind,
        )
    if kind is SlotKind.NON_VERB:
        return ArticulationLegalityVerdict(
            legality=ArticulationLegality.ILLEGAL_NON_VERB_FINITE_PREDICATE,
            predicate_kind=kind,
        )
    # Fail-open by design for UNKNOWN to preserve canary behavior.
    return ArticulationLegalityVerdict(
        legality=ArticulationLegality.LEGAL,
        predicate_kind=kind,
    )

