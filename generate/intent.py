"""Dialogue intent classification.

Maps a raw prompt string to a typed intent tag. The classifier is rule-based
(prefix/pattern matching) — no ML dependency. Downstream, the intent selects
the proposition frame family and graph shape before generation begins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, unique


@unique
class IntentTag(Enum):
    DEFINITION = "definition"
    CAUSE = "cause"
    PROCEDURE = "procedure"
    COMPARISON = "comparison"
    CORRECTION = "correction"
    RECALL = "recall"
    VERIFICATION = "verification"
    TRANSITIVE_QUERY = "transitive_query"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DialogueIntent:
    tag: IntentTag
    subject: str
    secondary_subject: str | None = None
    relation: str | None = None  # populated for TRANSITIVE_QUERY (ADR-0018)

    def requires_prior_turn(self) -> bool:
        return self.tag is IntentTag.CORRECTION


_COMPARE_RE = re.compile(
    r"^compare\s+(.+?)\s+(?:and|vs\.?|versus|with)\s+(.+)",
    re.IGNORECASE,
)

# Transitive-query forms (ADR-0018):
#   "What does X <verb>?"   -> (X, R) where R is any verb-like word
#   "Where does X belong?"  -> (X, belongs_to)
# The verb slot accepts any single word — `multi_relation_walk` in the
# operator layer handles unrecognised relations by falling back to a
# cross-relation traversal (rather than a strict literal-relation match).
_TRANSITIVE_QUERY_RE = re.compile(
    r"^what\s+does\s+(?P<subject>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)?)\s+"
    r"(?P<relation>[a-z][a-z\-]*)\b",
    re.IGNORECASE,
)
_BELONG_QUERY_RE = re.compile(
    r"^where\s+does\s+(?P<subject>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)?)\s+"
    r"belong(?:s?)\b",
    re.IGNORECASE,
)

# Normalisation of the relation surface form back to the bare relation
# vocabulary the teaching store carries (matches en_core_cognition_v1).
_RELATION_NORMALIZE: dict[str, str] = {
    "precede": "precedes", "precedes": "precedes",
    "cause": "causes", "causes": "causes",
    "ground": "grounds", "grounds": "grounds",
    "reveal": "reveals", "reveals": "reveals",
    "mean": "means", "means": "means",
    "follow": "follows", "follows": "follows",
    "contrast": "contrasts_with", "contrast_with": "contrasts_with",
    "contrasts_with": "contrasts_with", "contrasts with": "contrasts_with",
    "produce": "produces", "produces": "produces",
}

_RULES: tuple[tuple[re.Pattern[str], IntentTag], ...] = (
    (re.compile(r"^what\s+(?:is|are)\s+", re.IGNORECASE), IntentTag.DEFINITION),
    (re.compile(r"^why\s+", re.IGNORECASE), IntentTag.CAUSE),
    (re.compile(r"^how\s+(?:do|can|should|would)\s+(?:I|we|you)\s+", re.IGNORECASE), IntentTag.PROCEDURE),
    (re.compile(r"^(?:is|are|does|do|can|could|would|should|was|were|has|have|will)\s+.+\??\s*$", re.IGNORECASE), IntentTag.VERIFICATION),
    (re.compile(r"^(?:no|that'?s\s+(?:not|wrong)|incorrect|actually|correction)", re.IGNORECASE), IntentTag.CORRECTION),
    (re.compile(r"^remember\s+", re.IGNORECASE), IntentTag.RECALL),
)


def classify_intent(prompt: str) -> DialogueIntent:
    text = prompt.strip()
    if not text:
        return DialogueIntent(tag=IntentTag.UNKNOWN, subject="")

    compare_match = _COMPARE_RE.match(text)
    if compare_match:
        return DialogueIntent(
            tag=IntentTag.COMPARISON,
            subject=compare_match.group(1).strip(),
            secondary_subject=compare_match.group(2).strip(),
        )

    transitive_match = _TRANSITIVE_QUERY_RE.match(text)
    if transitive_match:
        raw_relation = transitive_match.group("relation").lower().strip()
        relation = _RELATION_NORMALIZE.get(raw_relation, raw_relation)
        return DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject=transitive_match.group("subject").strip(),
            relation=relation,
        )

    belong_match = _BELONG_QUERY_RE.match(text)
    if belong_match:
        return DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject=belong_match.group("subject").strip(),
            relation="belongs_to",
        )

    for pattern, tag in _RULES:
        match = pattern.match(text)
        if match:
            subject = text[match.end():].rstrip("?").strip()
            if not subject:
                subject = text
            return DialogueIntent(tag=tag, subject=subject)

    return DialogueIntent(tag=IntentTag.UNKNOWN, subject=text)
