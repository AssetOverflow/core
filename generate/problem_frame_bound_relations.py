"""ProblemFrame bound relation and target helpers.

This module owns the phase that turns grounded mentions, bindings, proposals, and
unary-delta cues into quantity-kind dispositions, ``BoundRelation`` records, and
bound question targets.  It does not assess contracts or create proposals.
"""

from __future__ import annotations

import re

from generate.construction_affordances import ConstructionProposal
from generate.kernel_facts import (
    BoundRelation,
    BoundRole,
    GroundedMention,
    MentionBinding,
    SourceSpan,
)
from generate.problem_frame import (
    BoundQuestionTarget,
    GroundedUnaryDeltaCue,
    QuantityKindDisposition,
)
from generate.problem_frame_extractors import _sentence_contains_current_or_now

_QUESTION_ENTITY_RE = re.compile(
    r"\bhow\s+(?:many|much)\s+(?:more\s+)?(?P<entity>[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)
_DECREASE_STATE_RE = re.compile(
    r"(?P<state>[A-Za-z][A-Za-z'-]*)\s+will\s+decrease\s+to",
    re.IGNORECASE,
)
_DECREASE_DELTA_QUESTION_RE = re.compile(
    r"\bwhat\s+will\s+the\s+(?P<entity>[A-Za-z][A-Za-z'-]*)\s+decrease\s+by\??",
    re.IGNORECASE,
)

# Duplicated intentionally to preserve phase-local ownership.
# Do not import another phase's internals just to share this regex.
_COPULAR_PARTITION_RE = re.compile(
    r"\b(?P<quantity>half|third|quarter)\b\s+of\s+(?:the\s+)?"
    r"(?P<whole>[A-Za-z][A-Za-z'-]*)\s+(?:are|is)\s+(?P<part>[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)

# Duplicated intentionally to preserve phase-local ownership.
# Do not import another phase's internals just to share this regex.
_DECREASE_TO_FRACTION_RE = re.compile(
    r"(?P<transition>decrease\s+to)\s+(?P<fraction>\d+\s*/\s*\d+)\s+of",
    re.IGNORECASE,
)

# Duplicated intentionally to preserve phase-local ownership.
# Do not import another phase's internals just to share this regex.
_TRANSFER_RE = re.compile(
    r"\b(?P<agent>[A-Z][A-Za-z'-]*)\s+(?:gave|gives|give|handed|passed)\s+"
    r"(?P<patient>[A-Z][A-Za-z'-]*)\s+"
    r"(?P<quantity>\d+(?:\.\d+)?)\s+(?P<object>[A-Za-z][A-Za-z'-]*)",
)


def _quantity_kind_dispositions(
    text: str,
    mentions: tuple[GroundedMention, ...],
    bindings: tuple[MentionBinding, ...],
    proposals: tuple[ConstructionProposal, ...],
) -> tuple[QuantityKindDisposition, ...]:
    """Close kind only for the exact proposal-backed local binding."""

    quantity_entity_proposals = tuple(
        proposal
        for proposal in proposals
        if proposal.family_id == "binding.quantity_entity"
    )
    if len(quantity_entity_proposals) != 1:
        return ()
    quantity_entity_proposal = quantity_entity_proposals[0]

    mentions_by_id = {mention.mention_id: mention for mention in mentions}
    unit_bindings: dict[str, list[MentionBinding]] = {}
    for binding in bindings:
        if binding.binding_type == "quantity_unit":
            unit_bindings.setdefault(binding.source_mention_id, []).append(binding)

    dispositions: list[QuantityKindDisposition] = []
    for binding in bindings:
        if binding.binding_type != "quantity_entity":
            continue
        quantity = mentions_by_id.get(binding.source_mention_id)
        entity = mentions_by_id.get(binding.target_mention_id)
        if quantity is None or entity is None or quantity.fact_id is None:
            continue
        if not any(
            cue.start <= quantity.span.start and entity.span.end <= cue.end
            for cue in quantity_entity_proposal.evidence_spans
        ):
            continue

        bound_units = unit_bindings.get(quantity.mention_id, [])
        if not bound_units:
            dispositions.append(
                QuantityKindDisposition(
                    quantity_mention_id=quantity.mention_id,
                    entity_mention_id=entity.mention_id,
                    quantity_kind="count",
                    unit_mention_id=None,
                    evidence_spans=binding.evidence_spans,
                )
            )
            continue
        if len(bound_units) != 1:
            continue

        unit_binding = bound_units[0]
        unit = mentions_by_id.get(unit_binding.target_mention_id)
        if unit is None or unit.span == entity.span:
            continue
        evidence = {
            (span.start, span.end, span.text): span
            for span in (*binding.evidence_spans, *unit_binding.evidence_spans)
        }
        dispositions.append(
            QuantityKindDisposition(
                quantity_mention_id=quantity.mention_id,
                entity_mention_id=entity.mention_id,
                quantity_kind="measurement",
                unit_mention_id=unit.mention_id,
                evidence_spans=tuple(evidence[key] for key in sorted(evidence)),
            )
        )

    return tuple(dispositions)


def _bound_relations(
    text: str,
    mentions: tuple[GroundedMention, ...],
    bindings: tuple[MentionBinding, ...],
    proposals: tuple[ConstructionProposal, ...],
    unary_delta_cues: tuple[GroundedUnaryDeltaCue, ...],
) -> tuple[BoundRelation, ...]:
    by_id = {m.mention_id: m for m in mentions}
    relations: list[BoundRelation] = []
    quantity_entity = [b for b in bindings if b.binding_type == "quantity_entity"]
    whole = next(
        (
            binding
            for binding in quantity_entity
            if "%" not in by_id[binding.source_mention_id].surface
            and by_id[binding.source_mention_id].surface.lower()
            not in {"half", "third", "quarter"}
        ),
        None,
    )
    for binding in quantity_entity:
        quantity = by_id[binding.source_mention_id]
        part = by_id[binding.target_mention_id]
        canonical_part = min(
            (
                mention
                for mention in mentions
                if mention.kind == part.kind
                and mention.surface.lower() == part.surface.lower()
            ),
            key=lambda mention: mention.span.start,
            default=part,
        )
        if "%" not in quantity.surface and quantity.surface.lower() not in {
            "half",
            "third",
            "quarter",
        }:
            continue
        roles = [
            BoundRole(
                "part",
                canonical_part.mention_id,
                canonical_part.kind,
                (canonical_part.span,),
            ),
            BoundRole("scale", quantity.mention_id, quantity.kind, (quantity.span,)),
        ]
        if whole is not None:
            whole_entity = by_id[whole.target_mention_id]
            roles.insert(
                0,
                BoundRole(
                    "whole",
                    whole_entity.mention_id,
                    whole_entity.kind,
                    (whole_entity.span,),
                ),
            )
        relation_type = (
            "percent_of" if "%" in quantity.surface else "subgroup_partition"
        )
        relations.append(
            BoundRelation(
                relation_id="",
                relation_type=relation_type,
                roles=tuple(roles),
                evidence_spans=tuple(
                    span for role in roles for span in role.evidence_spans
                ),
            )
        )

    for match in _COPULAR_PARTITION_RE.finditer(text):
        quantity = next(
            (
                m
                for m in mentions
                if m.kind == "quantity" and m.span.start == match.start("quantity")
            ),
            None,
        )
        whole = next(
            (
                m
                for m in mentions
                if m.kind == "object" and m.span.start == match.start("whole")
            ),
            None,
        )
        part = next(
            (
                m
                for m in mentions
                if m.kind == "object" and m.span.start == match.start("part")
            ),
            None,
        )
        if quantity is None or whole is None or part is None:
            continue
        canonical_whole = min(
            (
                mention
                for mention in mentions
                if mention.kind == "object"
                and mention.surface.lower() == whole.surface.lower()
            ),
            key=lambda mention: mention.span.start,
            default=whole,
        )
        roles = (
            BoundRole(
                "whole",
                canonical_whole.mention_id,
                canonical_whole.kind,
                (canonical_whole.span,),
            ),
            BoundRole("part", part.mention_id, part.kind, (part.span,)),
            BoundRole("scale", quantity.mention_id, quantity.kind, (quantity.span,)),
        )
        relations.append(
            BoundRelation(
                relation_id="",
                relation_type="subgroup_partition",
                roles=roles,
                evidence_spans=(quantity.span, canonical_whole.span, part.span),
            )
        )

    unary_delta_proposals = tuple(
        proposal
        for proposal in proposals
        if proposal.family_id == "state_change.unary_delta"
    )
    if len(unary_delta_proposals) == 1:
        proposal = unary_delta_proposals[0]
        if len(proposal.evidence_spans) == 1:
            cue_span = proposal.evidence_spans[0]
            cue_surface = text[cue_span.start : cue_span.end]
            if cue_span.text == cue_surface and cue_surface in {"gained", "lost"}:
                direction = "increase" if cue_surface == "gained" else "decrease"
                # Locate corresponding GroundedUnaryDeltaCue's cue_id
                cue_id = None
                for cue in unary_delta_cues:
                    if cue.span.start == cue_span.start and cue.span.end == cue_span.end:
                        cue_id = cue.cue_id
                        break
                if cue_id is not None:
                    matching_bindings = []
                    for binding in quantity_entity:
                        qty = by_id.get(binding.source_mention_id)
                        obj = by_id.get(binding.target_mention_id)
                        if qty is not None and obj is not None:
                            if (
                                cue_span.end <= qty.span.start
                                and qty.span.end <= obj.span.start
                            ):
                                segment = text[cue_span.start : obj.span.end]
                                if not any(marker in segment for marker in ".!?"):
                                    matching_bindings.append((binding, qty, obj))
                    if len(matching_bindings) == 1:
                        binding, quantity, obj = matching_bindings[0]
                        roles = (
                            BoundRole(
                                "action_cue",
                                cue_id,
                                "span",
                                (cue_span,),
                            ),
                            BoundRole(
                                "delta_quantity",
                                quantity.mention_id,
                                quantity.kind,
                                (quantity.span,),
                            ),
                            BoundRole(
                                "changed_object", obj.mention_id, obj.kind, (obj.span,)
                            ),
                            BoundRole("direction", direction, "direction", (cue_span,)),
                        )
                        relations.append(
                            BoundRelation(
                                relation_id="",
                                relation_type="unary_delta",
                                roles=roles,
                                evidence_spans=(cue_span, quantity.span, obj.span),
                            )
                        )

    decrease_matches = list(_DECREASE_TO_FRACTION_RE.finditer(text))
    if len(decrease_matches) == 1:
        match = decrease_matches[0]
        scale = next(
            (
                m
                for m in mentions
                if m.kind == "quantity" and m.span.start == match.start("fraction")
            ),
            None,
        )
        state_match = next(
            (
                item
                for item in _DECREASE_STATE_RE.finditer(text)
                if item.start("state") < match.start("transition")
            ),
            None,
        )
        state = (
            next(
                (
                    m
                    for m in mentions
                    if m.kind == "object"
                    and state_match is not None
                    and m.span.start == state_match.start("state")
                ),
                None,
            )
            if state_match is not None
            else None
        )
        unit_binding_by_quantity = {
            binding.source_mention_id: binding
            for binding in bindings
            if binding.binding_type == "quantity_unit"
        }
        base_candidates = [
            mention
            for mention in mentions
            if mention.kind == "quantity"
            and mention.mention_id != (scale.mention_id if scale else None)
            and mention.mention_id in unit_binding_by_quantity
            and _sentence_contains_current_or_now(text, mention.span.start)
        ]
        if len(base_candidates) == 1 and scale is not None and state is not None:
            base = base_candidates[0]
            base_unit_binding = unit_binding_by_quantity.get(base.mention_id)
            roles = [
                BoundRole("base_quantity", base.mention_id, base.kind, (base.span,)),
                BoundRole("scale", scale.mention_id, scale.kind, (scale.span,)),
                BoundRole("state_entity", state.mention_id, state.kind, (state.span,)),
                BoundRole(
                    "transition",
                    f"span:{match.start('transition')}:{match.end('transition')}",
                    "span",
                    (
                        SourceSpan(
                            text[match.start("transition") : match.end("transition")],
                            match.start("transition"),
                            match.end("transition"),
                        ),
                    ),
                ),
            ]
            if base_unit_binding is not None:
                unit = by_id.get(base_unit_binding.target_mention_id)
                if unit is not None:
                    roles.append(
                        BoundRole("unit", unit.mention_id, unit.kind, (unit.span,))
                    )
            relations.append(
                BoundRelation(
                    relation_id="",
                    relation_type="decrease_to_fraction",
                    roles=tuple(roles),
                    evidence_spans=tuple(
                        span for role in roles for span in role.evidence_spans
                    ),
                )
            )

    for match in _TRANSFER_RE.finditer(text):

        def at(group: str, kind: str) -> GroundedMention | None:
            return next(
                (
                    m
                    for m in mentions
                    if m.kind == kind and m.span.start == match.start(group)
                ),
                None,
            )

        agent = at("agent", "actor")
        patient = at("patient", "actor")
        quantity = at("quantity", "quantity")
        obj = at("object", "object")
        if all((agent, patient, quantity, obj)):
            assert agent and patient and quantity and obj
            roles = tuple(
                BoundRole(name, mention.mention_id, mention.kind, (mention.span,))
                for name, mention in (
                    ("agent", agent),
                    ("patient", patient),
                    ("quantity", quantity),
                    ("object", obj),
                )
            )
            relations.append(
                BoundRelation(
                    "",
                    "transfer",
                    roles,
                    tuple(m.span for m in (agent, patient, quantity, obj)),
                )
            )

    relations.sort(key=lambda r: (r.evidence_spans[0].start, r.relation_type))
    return tuple(
        BoundRelation(
            f"bound-rel-{index:04d}",
            relation.relation_type,
            relation.roles,
            relation.evidence_spans,
        )
        for index, relation in enumerate(relations)
    )


def _bound_question_target(
    text: str, mentions: tuple[GroundedMention, ...]
) -> BoundQuestionTarget | None:
    """Extract and bind the question target from the problem text.

    Priority Cascade Order:
    1. Specific regex-based triggers:
       - Proportional decrease delta: checked first using ``_DECREASE_DELTA_QUESTION_RE``.
         If matched, returns a difference/delta/decrease target.
    2. General question clause extraction:
       - Triggers on ``_QUESTION_ENTITY_RE``.
       - If no match, but "?" is present in the text, returns an "unknown" target.
    3. Target classification of the question clause:
       - "more" -> difference / delta / unknown direction.
       - Initial state indicators ("were in", "was in", "started with", "originally") -> count / initial / inverse.
       - Remaining indicators ("remaining", "left" in context) -> count / final / remaining.
       - Aggregate indicators ("total", "altogether", "own") -> count / aggregate / forward.
       - Portion percentage ("percent", "percentage") -> portion / final / forward.
       - Portion fraction ("ratio", "fraction") -> portion / final / forward.
       - Fallback -> count / final / forward.
    """
    decrease_delta = _DECREASE_DELTA_QUESTION_RE.search(text)
    if decrease_delta is not None:
        entity_surface = decrease_delta.group("entity")
        entity = next(
            (
                m
                for m in mentions
                if m.kind == "object" and m.surface.lower() == entity_surface.lower()
            ),
            None,
        )
        span = SourceSpan(
            text[decrease_delta.start() : decrease_delta.end()],
            decrease_delta.start(),
            decrease_delta.end(),
        )
        return BoundQuestionTarget(
            "difference",
            entity_surface,
            entity.mention_id if entity else None,
            "delta_quantity",
            (span,),
            target_operator="difference",
            target_state="delta",
            target_direction="decrease",
        )
    question = _QUESTION_ENTITY_RE.search(text)
    if question is None:
        if "?" not in text:
            return None
        qmark = text.index("?")
        return BoundQuestionTarget(
            "unknown",
            "?",
            None,
            "unresolved",
            (SourceSpan("?", qmark, qmark + 1),),
            target_operator="unknown",
            target_state="unknown",
            target_direction="unknown",
        )
    entity = next(
        (
            m
            for m in mentions
            if m.kind == "object" and m.span.start == question.start("entity")
        ),
        None,
    )
    question_clause = text[question.start() :]
    prefix = text[max(0, question.start() - 32) : question.end()].lower()
    question_lower = question_clause.lower()
    if "more" in question.group(0).lower():
        target_type = "difference"
        target_operator = "difference"
        target_state = "delta"
        target_direction = "unknown"
        unknown_slot = "difference"
    elif any(
        x in question_lower for x in ("were in", "was in", "started with", "originally")
    ):
        target_type = "count"
        target_operator = "count"
        target_state = "initial"
        target_direction = "inverse"
        unknown_slot = "initial"
    elif any(x in prefix for x in ("remaining", "left")):
        target_type = "remaining"
        target_operator = "count"
        target_state = "final"
        target_direction = "remaining"
        unknown_slot = "remaining"
    elif any(x in question_lower for x in ("total", "altogether", "own")):
        target_type = "count"
        target_operator = "count"
        target_state = "aggregate"
        target_direction = "forward"
        unknown_slot = "count"
    else:
        target_type = "count"
        target_operator = "count"
        target_state = "current"
        target_direction = "unknown"
        unknown_slot = "count"
    span = SourceSpan(
        text[question.start() : question.end()], question.start(), question.end()
    )
    return BoundQuestionTarget(
        target_type,
        question.group("entity"),
        entity.mention_id if entity else None,
        unknown_slot,
        (span,),
        target_operator=target_operator,
        target_state=target_state,
        target_direction=target_direction,
    )
