"""Deterministic relation binding v1.

This module binds the narrow ``ParsedClaim`` records from
``language_packs.claim_parsing`` into explicit relation structures.  It is not a
solver and does not infer missing quantities or referents.  Claims that lack
enough operands remain unbound with a typed reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from language_packs.claim_parsing import ParsedClaim, parse_claim


BindingKind = Literal[
    "action_relation",
    "quantity_relation",
    "transfer_relation",
    "spatial_relation",
    "conditional_relation",
    "comparative_relation",
    "negated_relation",
    "residual_state_relation",
    "unbound",
]

BindingState = Literal["BOUND", "UNBOUND"]


@dataclass(frozen=True, slots=True)
class BoundRelation:
    """A deterministic relation binding over a parsed claim."""

    kind: BindingKind
    state: BindingState
    relation: str | None
    arguments: dict[str, object | None] = field(default_factory=dict)
    evidence_span: str = ""
    source_kind: str | None = None
    refusal_reason: str | None = None

    def as_dict(self) -> dict[str, object | None]:
        return {
            "kind": self.kind,
            "state": self.state,
            "relation": self.relation,
            "arguments": dict(self.arguments),
            "evidence_span": self.evidence_span,
            "source_kind": self.source_kind,
            "refusal_reason": self.refusal_reason,
        }


def _unbound(claim: ParsedClaim, reason: str) -> BoundRelation:
    return BoundRelation(
        kind="unbound",
        state="UNBOUND",
        relation=None,
        arguments={},
        evidence_span=claim.evidence_span,
        source_kind=claim.kind,
        refusal_reason=reason,
    )


def bind_claim(claim: ParsedClaim) -> BoundRelation:
    """Bind a parsed claim into an explicit relation when evidence is sufficient."""
    if claim.epistemic_state == "UNDETERMINED":
        return _unbound(claim, claim.refusal_reason or "undetermined_claim")

    if claim.kind == "simple_action":
        if not (claim.subject and claim.relation and claim.object):
            return _unbound(claim, "missing_action_operand")
        return BoundRelation(
            kind="action_relation",
            state="BOUND",
            relation=claim.relation,
            arguments={"agent": claim.subject, "object": claim.object},
            evidence_span=claim.evidence_span,
            source_kind=claim.kind,
        )

    if claim.kind == "quantity_possession":
        if not (claim.subject and claim.relation and claim.object and claim.quantity is not None):
            return _unbound(claim, "missing_quantity_operand")
        return BoundRelation(
            kind="quantity_relation",
            state="BOUND",
            relation="quantity_of",
            arguments={
                "owner": claim.subject,
                "attribute": claim.object,
                "quantity": claim.quantity,
                "surface_relation": claim.relation,
            },
            evidence_span=claim.evidence_span,
            source_kind=claim.kind,
        )

    if claim.kind == "ditransitive_transfer":
        if not (
            claim.subject
            and claim.relation
            and claim.object
            and claim.indirect_object
            and claim.quantity is not None
        ):
            return _unbound(claim, "missing_transfer_operand")
        return BoundRelation(
            kind="transfer_relation",
            state="BOUND",
            relation=claim.relation,
            arguments={
                "source_agent": claim.subject,
                "recipient": claim.indirect_object,
                "object": claim.object,
                "quantity": claim.quantity,
            },
            evidence_span=claim.evidence_span,
            source_kind=claim.kind,
        )

    if claim.kind == "spatial_relation":
        if not (claim.subject and claim.relation and claim.object):
            return _unbound(claim, "missing_spatial_operand")
        return BoundRelation(
            kind="spatial_relation",
            state="BOUND",
            relation=claim.relation,
            arguments={
                "figure": claim.subject,
                "ground": claim.object,
                "qualifiers": list(claim.qualifiers),
            },
            evidence_span=claim.evidence_span,
            source_kind=claim.kind,
        )

    if claim.kind == "conditional":
        if not (claim.antecedent and claim.consequent):
            return _unbound(claim, "missing_conditional_operand")
        return BoundRelation(
            kind="conditional_relation",
            state="BOUND",
            relation="if_then",
            arguments={"antecedent": claim.antecedent, "consequent": claim.consequent},
            evidence_span=claim.evidence_span,
            source_kind=claim.kind,
        )

    if claim.kind == "comparison":
        if not (claim.subject and claim.object and claim.comparator and claim.reference):
            return _unbound(claim, "missing_comparison_operand")
        return BoundRelation(
            kind="comparative_relation",
            state="BOUND",
            relation="compared_quantity",
            arguments={
                "left_entity": claim.subject,
                "attribute": claim.object,
                "comparator": claim.comparator,
                "right_entity": claim.reference,
                "delta": None,
            },
            evidence_span=claim.evidence_span,
            source_kind=claim.kind,
        )

    if claim.kind == "negated_possession":
        if not (claim.subject and claim.object):
            return _unbound(claim, "missing_negation_operand")
        return BoundRelation(
            kind="negated_relation",
            state="BOUND",
            relation="not_has",
            arguments={"owner": claim.subject, "attribute": claim.object},
            evidence_span=claim.evidence_span,
            source_kind=claim.kind,
        )

    if claim.kind == "temporal_state":
        if not (claim.subject and claim.quantity is not None):
            return _unbound(claim, "missing_temporal_operand")
        if claim.object is None:
            return _unbound(claim, "missing_residual_attribute")
        return BoundRelation(
            kind="residual_state_relation",
            state="BOUND",
            relation="had_left_after",
            arguments={
                "entity": claim.subject,
                "attribute": claim.object,
                "quantity": claim.quantity,
                "qualifiers": list(claim.qualifiers),
            },
            evidence_span=claim.evidence_span,
            source_kind=claim.kind,
        )

    return _unbound(claim, "unsupported_claim_kind")


def bind_text(text: str) -> BoundRelation:
    """Parse then bind one text surface."""
    return bind_claim(parse_claim(text))
