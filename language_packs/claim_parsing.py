"""Deterministic claim parsing substrate v1.

This module is intentionally narrow.  It is not a general natural-language
parser and does not repair malformed input.  It recognizes a small set of
foundation-curriculum sentence shapes and returns typed claim records with
source evidence spans, or a typed refusal when the sentence lacks enough
surface evidence.

The parser is designed as a bridge between ``en_core_syntax_v1`` vocabulary and
later relation-binding work.  It keeps extraction deterministic, auditable, and
scope-limited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal


ClaimKind = Literal[
    "simple_action",
    "quantity_possession",
    "ditransitive_transfer",
    "spatial_relation",
    "conditional",
    "comparison",
    "negated_possession",
    "temporal_state",
    "undetermined",
]

EpistemicState = Literal["EVIDENCED", "UNDETERMINED"]


@dataclass(frozen=True, slots=True)
class ParsedClaim:
    """One deterministic claim parse with exact evidence span."""

    kind: ClaimKind
    subject: str | None
    relation: str | None
    object: str | None
    evidence_span: str
    epistemic_state: EpistemicState
    quantity: int | None = None
    indirect_object: str | None = None
    qualifiers: tuple[str, ...] = field(default_factory=tuple)
    antecedent: str | None = None
    consequent: str | None = None
    comparator: str | None = None
    reference: str | None = None
    refusal_reason: str | None = None

    def as_dict(self) -> dict[str, object | None]:
        """Return a stable JSON-serializable representation."""
        return {
            "kind": self.kind,
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "quantity": self.quantity,
            "indirect_object": self.indirect_object,
            "qualifiers": list(self.qualifiers),
            "antecedent": self.antecedent,
            "consequent": self.consequent,
            "comparator": self.comparator,
            "reference": self.reference,
            "evidence_span": self.evidence_span,
            "epistemic_state": self.epistemic_state,
            "refusal_reason": self.refusal_reason,
        }


_ARTICLE_RE = re.compile(r"\b(?:a|an|the)\s+", re.IGNORECASE)
_SPACES_RE = re.compile(r"\s+")
_TERMINAL_RE = re.compile(r"[.?!]\s*$")

_CONDITIONAL_RE = re.compile(
    r"^if\s+(?P<antecedent>.+?),\s*(?P<consequent>.+?)\.?$",
    re.IGNORECASE,
)
_TEMPORAL_RE = re.compile(
    r"^after\s+(?P<event>.+?),\s*(?P<subject>[A-Z][A-Za-z]*)\s+had\s+"
    r"(?P<quantity>\d+)\s+(?P<object>[A-Za-z_ -]+?)\s+left\.?$",
)
_NEGATED_POSSESSION_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z]*)\s+does\s+not\s+have\s+"
    r"(?P<object>[A-Za-z_ -]+?)\.?$",
)
_DITRANSITIVE_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z]*)\s+(?P<verb>gave|gives|sent|sends)\s+"
    r"(?P<indirect>[A-Z][A-Za-z]*)\s+(?P<quantity>\d+)\s+"
    r"(?P<object>[A-Za-z_ -]+?)\.?$",
)
_QUANTITY_POSSESSION_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z]*)\s+(?P<verb>has|had|owns)\s+"
    r"(?P<quantity>\d+)\s+(?P<object>[A-Za-z_ -]+?)\.?$",
)
_SPATIAL_RE = re.compile(
    r"^(?:the\s+)?(?P<qualifier>[a-z]+)\s+(?P<subject>[a-z]+)\s+is\s+"
    r"(?P<relation>in|inside|on|above|below|near|between)\s+"
    r"(?:the\s+)?(?P<object>[A-Za-z_ -]+?)\.?$",
    re.IGNORECASE,
)
_COMPARISON_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z]*)\s+has\s+"
    r"(?P<comparator>more|fewer|less)\s+(?P<object>[A-Za-z_ -]+?)\s+than\s+"
    r"(?P<reference>[A-Z][A-Za-z]*)\.?$",
)
_SIMPLE_ACTION_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z]*)\s+(?P<verb>bought|buys|sold|sells|made|makes|created|creates)\s+"
    r"(?P<object>[A-Za-z_ -]+?)\.?$",
)


def _clean(value: str) -> str:
    value = _TERMINAL_RE.sub("", value.strip())
    value = _ARTICLE_RE.sub("", value)
    return _SPACES_RE.sub(" ", value).strip()


def _undetermined(text: str, reason: str) -> ParsedClaim:
    return ParsedClaim(
        kind="undetermined",
        subject=None,
        relation=None,
        object=None,
        evidence_span=text.strip(),
        epistemic_state="UNDETERMINED",
        refusal_reason=reason,
    )


def parse_claim(text: str) -> ParsedClaim:
    """Parse one narrow foundation-curriculum sentence.

    Returns ``ParsedClaim(kind="undetermined", epistemic_state="UNDETERMINED")``
    when the sentence is outside the v1 grammar or lacks enough evidence for the
    requested claim.  The parser never guesses a missing quantity, referent, or
    relation.
    """
    evidence = _SPACES_RE.sub(" ", text.strip())
    if not evidence:
        return _undetermined("", "empty_input")

    if "?" in evidence:
        if re.search(r"\bfewer\b|\bmore\b|\bless\b", evidence, re.IGNORECASE):
            return _undetermined(evidence, "insufficient_quantity_evidence")
        return _undetermined(evidence, "question_not_claim")

    if match := _CONDITIONAL_RE.match(evidence):
        antecedent = _clean(match.group("antecedent"))
        consequent = _clean(match.group("consequent"))
        return ParsedClaim(
            kind="conditional",
            subject=None,
            relation="if_then",
            object=None,
            antecedent=antecedent,
            consequent=consequent,
            evidence_span=evidence,
            epistemic_state="EVIDENCED",
        )

    if match := _TEMPORAL_RE.match(evidence):
        return ParsedClaim(
            kind="temporal_state",
            subject=match.group("subject"),
            relation="had_left_after",
            object=_clean(match.group("object")),
            quantity=int(match.group("quantity")),
            qualifiers=(f"after {_clean(match.group('event'))}",),
            evidence_span=evidence,
            epistemic_state="EVIDENCED",
        )

    if match := _NEGATED_POSSESSION_RE.match(evidence):
        return ParsedClaim(
            kind="negated_possession",
            subject=match.group("subject"),
            relation="does_not_have",
            object=_clean(match.group("object")),
            evidence_span=evidence,
            epistemic_state="EVIDENCED",
        )

    if match := _DITRANSITIVE_RE.match(evidence):
        return ParsedClaim(
            kind="ditransitive_transfer",
            subject=match.group("subject"),
            relation=match.group("verb").lower(),
            object=_clean(match.group("object")),
            quantity=int(match.group("quantity")),
            indirect_object=match.group("indirect"),
            evidence_span=evidence,
            epistemic_state="EVIDENCED",
        )

    if match := _QUANTITY_POSSESSION_RE.match(evidence):
        return ParsedClaim(
            kind="quantity_possession",
            subject=match.group("subject"),
            relation=match.group("verb").lower(),
            object=_clean(match.group("object")),
            quantity=int(match.group("quantity")),
            evidence_span=evidence,
            epistemic_state="EVIDENCED",
        )

    if match := _SPATIAL_RE.match(evidence):
        return ParsedClaim(
            kind="spatial_relation",
            subject=_clean(match.group("subject")),
            relation=match.group("relation").lower(),
            object=_clean(match.group("object")),
            qualifiers=(_clean(match.group("qualifier")),),
            evidence_span=evidence,
            epistemic_state="EVIDENCED",
        )

    if match := _COMPARISON_RE.match(evidence):
        return ParsedClaim(
            kind="comparison",
            subject=match.group("subject"),
            relation="has_compared_quantity",
            object=_clean(match.group("object")),
            comparator=match.group("comparator").lower(),
            reference=match.group("reference"),
            evidence_span=evidence,
            epistemic_state="EVIDENCED",
        )

    if match := _SIMPLE_ACTION_RE.match(evidence):
        return ParsedClaim(
            kind="simple_action",
            subject=match.group("subject"),
            relation=match.group("verb").lower(),
            object=_clean(match.group("object")),
            evidence_span=evidence,
            epistemic_state="EVIDENCED",
        )

    return _undetermined(evidence, "unmatched_v1_claim_shape")
