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
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DialogueIntent:
    tag: IntentTag
    subject: str
    secondary_subject: str | None = None

    def requires_prior_turn(self) -> bool:
        return self.tag is IntentTag.CORRECTION


_COMPARE_RE = re.compile(
    r"^compare\s+(.+?)\s+(?:and|vs\.?|versus|with)\s+(.+)",
    re.IGNORECASE,
)

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

    for pattern, tag in _RULES:
        match = pattern.match(text)
        if match:
            subject = text[match.end():].rstrip("?").strip()
            if not subject:
                subject = text
            return DialogueIntent(tag=tag, subject=subject)

    return DialogueIntent(tag=IntentTag.UNKNOWN, subject=text)
