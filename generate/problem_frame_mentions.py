"""ProblemFrame mention and binding helpers.

This module owns grounded mention extraction and mention-binding edges.  It does
not create construction proposals, assess contracts, or mutate builder state.
"""

from __future__ import annotations

import re

from generate.kernel_facts import (
    GroundedMention,
    GroundedScalar,
    GroundedUnit,
    MentionBinding,
    SourceSpan,
)

_ENTITY_AFTER_QUANTITY_RE = re.compile(
    r"(?P<quantity>\d+(?:\.\d+)?\s*%?)\s+(?:of\s+(?:the\s+)?)?"
    r"(?P<entity>[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)
_FRACTION_ENTITY_RE = re.compile(
    r"\b(?P<quantity>half|third|quarter)\b\s+(?:of\s+(?:the\s+)?|are\s+|the\s+)?"
    r"(?P<entity>[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)
_QUESTION_ENTITY_RE = re.compile(
    r"\bhow\s+(?:many|much)\s+(?:more\s+)?(?P<entity>[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)
_COPULAR_PARTITION_RE = re.compile(
    r"\b(?P<quantity>half|third|quarter)\b\s+of\s+(?:the\s+)?"
    r"(?P<whole>[A-Za-z][A-Za-z'-]*)\s+(?:are|is)\s+(?P<part>[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)
_DECREASE_STATE_RE = re.compile(
    r"(?P<state>[A-Za-z][A-Za-z'-]*)\s+will\s+decrease\s+to",
    re.IGNORECASE,
)
_ACTOR_VERB_RE = re.compile(
    r"\b(?P<actor>[A-Z][A-Za-z'-]*)\s+"
    r"(?:gave|gives|give|received|receives|spent|spends|ate|eats|bought|buys|sold|sells)\b"
)
_TRANSFER_RE = re.compile(
    r"\b(?P<agent>[A-Z][A-Za-z'-]*)\s+(?:gave|gives|give|handed|passed)\s+"
    r"(?P<patient>[A-Z][A-Za-z'-]*)\s+"
    r"(?P<quantity>\d+(?:\.\d+)?)\s+(?P<object>[A-Za-z][A-Za-z'-]*)",
)


def _extract_mentions(
    text: str,
    quantities: tuple[GroundedScalar, ...],
    units: tuple[GroundedUnit, ...],
) -> tuple[GroundedMention, ...]:
    records: dict[tuple[str, int, int], GroundedMention] = {}

    def add(kind: str, start: int, end: int, *, fact_id: str | None = None) -> None:
        key = (kind, start, end)
        if key in records:
            return
        records[key] = GroundedMention(
            mention_id="",
            kind=kind,
            surface=text[start:end],
            span=SourceSpan(text[start:end], start, end),
            fact_id=fact_id,
        )

    for quantity in quantities:
        span = quantity.provenance.source_spans[0]
        add("quantity", span.start, span.end, fact_id=quantity.fact_id)
    for unit in units:
        span = unit.provenance.source_spans[0]
        add("unit", span.start, span.end, fact_id=unit.fact_id)
    for pattern in (
        _ENTITY_AFTER_QUANTITY_RE,
        _FRACTION_ENTITY_RE,
        _QUESTION_ENTITY_RE,
    ):
        for match in pattern.finditer(text):
            add("object", match.start("entity"), match.end("entity"))
    for match in _COPULAR_PARTITION_RE.finditer(text):
        add("object", match.start("whole"), match.end("whole"))
        add("object", match.start("part"), match.end("part"))
    for match in _DECREASE_STATE_RE.finditer(text):
        add("object", match.start("state"), match.end("state"))
    for match in _ACTOR_VERB_RE.finditer(text):
        add("actor", match.start("actor"), match.end("actor"))
    for match in _TRANSFER_RE.finditer(text):
        add("actor", match.start("agent"), match.end("agent"))
        add("actor", match.start("patient"), match.end("patient"))
        add("object", match.start("object"), match.end("object"))

    ordered = sorted(
        records.values(),
        key=lambda m: (m.span.start, m.span.end, m.kind, m.surface.lower()),
    )
    return tuple(
        GroundedMention(
            mention_id=f"mention-{index:04d}",
            kind=m.kind,
            surface=m.surface,
            span=m.span,
            fact_id=m.fact_id,
        )
        for index, m in enumerate(ordered)
    )


def _extract_bindings(
    text: str,
    mentions: tuple[GroundedMention, ...],
) -> tuple[MentionBinding, ...]:
    by_span_kind = {(m.span.start, m.span.end, m.kind): m for m in mentions}
    quantities = [m for m in mentions if m.kind == "quantity"]
    bindings: list[MentionBinding] = []
    seen: set[tuple[str, str, str]] = set()

    def bind(
        binding_type: str, source: GroundedMention, target: GroundedMention
    ) -> None:
        key = (binding_type, source.mention_id, target.mention_id)
        if key in seen:
            return
        seen.add(key)
        bindings.append(
            MentionBinding(
                binding_id="",
                binding_type=binding_type,
                source_mention_id=source.mention_id,
                target_mention_id=target.mention_id,
                evidence_spans=(source.span, target.span),
            )
        )

    for pattern in (_ENTITY_AFTER_QUANTITY_RE, _FRACTION_ENTITY_RE):
        for match in pattern.finditer(text):
            entity = by_span_kind.get(
                (match.start("entity"), match.end("entity"), "object")
            )
            if entity is None:
                continue
            candidates = [
                q for q in quantities if q.span.start == match.start("quantity")
            ]
            if candidates:
                bind("quantity_entity", candidates[0], entity)
    units = [m for m in mentions if m.kind == "unit"]
    for quantity in quantities:
        following = [
            unit
            for unit in units
            if unit.span.start >= quantity.span.end
            and not text[quantity.span.end : unit.span.start].strip()
        ]
        if following:
            bind("quantity_unit", quantity, min(following, key=lambda u: u.span.start))

    ordered = sorted(
        bindings,
        key=lambda b: (b.evidence_spans[0].start, b.binding_type, b.target_mention_id),
    )
    return tuple(
        MentionBinding(
            binding_id=f"binding-{index:04d}",
            binding_type=b.binding_type,
            source_mention_id=b.source_mention_id,
            target_mention_id=b.target_mention_id,
            evidence_spans=b.evidence_spans,
        )
        for index, b in enumerate(ordered)
    )
