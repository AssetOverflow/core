"""ProblemFrame builder — substrate-backed construction from raw problem text.

Operationalizes the #829 kernel substrate path:

    raw text → scalar/unit/hazard/process-frame facts → ProblemFrame

Non-goals:
  - answer derivation
  - case-id behavior
  - serving admission
  - guessing unsupported or ambiguous surfaces
"""
from __future__ import annotations

import dataclasses
import re
from fractions import Fraction

from generate.construction_affordances import ConstructionProposal, propose_construction
from generate.kernel_facts import (
    BoundRelation,
    BoundRole,
    CandidateRelation,
    GroundedMention,
    GroundedScalar,
    GroundedUnit,
    KernelHazard,
    KernelProvenance,
    MentionBinding,
    RelationRole,
    SourceSpan,
)
from generate.problem_frame import (
    BoundQuestionTarget,
    ProblemFrame,
    ProblemFrameBuilder,
    QuantityKindDisposition,
    QuestionTarget,
)
from generate.process_frames import ProcessFrame, all_frames
from language_packs.ambiguity_hazards import (
    AmbiguityHazard,
    all_registered_surfaces,
    lookup_hazards,
)
from language_packs.scalar_equivalence import (
    ScalarCandidate,
    extract_scalar_candidates,
)
from language_packs.unit_dimensions import classify_dimension

_UNIT_TOKEN_RE: re.Pattern[str] = re.compile(r"\b\d+(?:\.\d+)?\s+([a-zA-Z]+)\b")

_UNIT_STOPWORDS: frozenset[str] = frozenset({
    "more", "less", "times", "percent", "percentage", "of", "and", "or",
    "the", "a", "an", "in", "to", "for", "with", "at", "by", "from",
    "each", "per", "way", "ways",
})

_ORDINAL_SUFFIX_RE: re.Pattern[str] = re.compile(
    r"\b(half|third|quarter)\s+(place|position|grade|rank)\b",
    re.IGNORECASE,
)


def surface_in_text(surface: str, text: str) -> bool:
    """Match a registered surface at lexical, including punctuation, boundaries."""
    return re.search(
        rf"(?<![\w]){re.escape(surface)}(?![\w])",
        text,
        flags=re.IGNORECASE,
    ) is not None


def _hazard_to_kernel(hazard: AmbiguityHazard) -> KernelHazard:
    return KernelHazard(
        hazard_id=hazard.hazard_id,
        category=hazard.category,
        surface=hazard.surface,
        description=hazard.description,
        context_required=hazard.context_required,
    )


def _extract_unit_candidates(text: str) -> tuple[GroundedUnit, ...]:
    units: list[GroundedUnit] = []
    seen: set[tuple[str, int, int]] = set()

    for match in _UNIT_TOKEN_RE.finditer(text):
        token = match.group(1)
        token_lower = token.lower()
        if token_lower in _UNIT_STOPWORDS:
            continue
        dim_fact = classify_dimension(token_lower)
        if dim_fact is None:
            continue
        start = match.start(1)
        end = match.end(1)
        key = (token_lower, start, end)
        if key in seen:
            continue
        seen.add(key)
        span = SourceSpan(text[start:end], start, end)
        provenance = KernelProvenance(kind="problem_text", source_spans=(span,))
        units.append(
            GroundedUnit(
                fact_id=f"unit-{len(units):04d}",
                surface=token_lower,
                dimension=dim_fact.dimension,
                singular=dim_fact.singular,
                provenance=provenance,
            )
        )

    return tuple(sorted(units, key=lambda u: (u.provenance.source_spans[0].start, u.surface)))


def _extract_hazards(text: str) -> tuple[KernelHazard, ...]:
    text_lower = text.lower()
    hazards: list[KernelHazard] = []
    seen: set[str] = set()

    for surface in all_registered_surfaces():
        if not surface_in_text(surface, text_lower):
            continue
        for hazard in lookup_hazards(surface):
            if hazard.hazard_id in seen:
                continue
            seen.add(hazard.hazard_id)
            hazards.append(_hazard_to_kernel(hazard))

    if "%" in text:
        for hazard in lookup_hazards("percent"):
            if hazard.hazard_id in seen:
                continue
            seen.add(hazard.hazard_id)
            hazards.append(_hazard_to_kernel(hazard))

    return tuple(sorted(hazards, key=lambda h: h.hazard_id))


def _is_ordinal_scalar_span(text: str, start: int, end: int) -> bool:
    """Refuse fraction readings for ordinals like ``third place``."""
    window_start = max(0, start - 20)
    window_end = min(len(text), end + 20)
    window = text[window_start:window_end]
    for match in _ORDINAL_SUFFIX_RE.finditer(window):
        abs_start = window_start + match.start()
        abs_end = window_start + match.end()
        if start >= abs_start and end <= abs_end:
            return True
    return False


def _filter_scalar_candidates(
    text: str,
    candidates: tuple[ScalarCandidate, ...],
) -> tuple[ScalarCandidate, ...]:
    kept: list[ScalarCandidate] = []
    for candidate in candidates:
        if candidate.source_span is None:
            kept.append(candidate)
            continue
        start, end = candidate.source_span
        if _is_ordinal_scalar_span(text, start, end):
            continue
        kept.append(candidate)
    return tuple(kept)


def _trigger_span(text: str, trigger: str) -> SourceSpan | None:
    match = re.search(
        rf"(?<![\w]){re.escape(trigger)}(?![\w])",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return SourceSpan(text[match.start():match.end()], match.start(), match.end())


def _sentence_contains_current_or_now(text: str, index: int) -> bool:
    start = max(
        text.rfind(".", 0, index),
        text.rfind("?", 0, index),
        text.rfind("!", 0, index),
    )
    end_candidates = [
        pos for pos in (
            text.find(".", index),
            text.find("?", index),
            text.find("!", index),
        )
        if pos != -1
    ]
    end = min(end_candidates) if end_candidates else len(text)
    sentence = text[start + 1:end].lower()
    return "current" in sentence or "now" in sentence


def _extract_process_frame_candidates(text: str) -> tuple[ProcessFrame, ...]:
    text_lower = text.lower()
    matched: dict[str, ProcessFrame] = {}

    for frame in all_frames():
        for trigger in frame.trigger_surfaces:
            if surface_in_text(trigger, text_lower):
                matched[frame.name] = frame
                break

    return tuple(matched[name] for name in sorted(matched))


def _frame_roles(frame: ProcessFrame) -> tuple[RelationRole, ...]:
    roles: list[RelationRole] = []
    for role in frame.required_roles:
        roles.append(RelationRole(role.name, True, role.description))
    for role in frame.optional_roles:
        roles.append(RelationRole(role.name, False, role.description))
    return tuple(roles)


def _extract_candidate_relations(
    text: str,
    frames: tuple[ProcessFrame, ...],
) -> tuple[CandidateRelation, ...]:
    relations: list[CandidateRelation] = []

    for frame in frames:
        span: SourceSpan | None = None
        for trigger in frame.trigger_surfaces:
            span = _trigger_span(text, trigger)
            if span is not None:
                break
        provenance = (
            KernelProvenance(kind="problem_text", source_spans=(span,))
            if span is not None
            else None
        )
        frame_hazards = tuple(
            KernelHazard(
                hazard_id=f"frame-{frame.name}-{category}",
                category=category,
                surface=frame.name,
                description=f"Process frame {frame.name} hazard {category}",
            )
            for category in frame.hazards
        )
        relations.append(
            CandidateRelation(
                relation_id=f"rel-{frame.name}",
                relation_type=frame.candidate_relation,
                roles=_frame_roles(frame),
                provenance=provenance,
                hazards=frame_hazards,
            )
        )

    return tuple(relations)


def _scalar_to_grounded(
    candidate: ScalarCandidate,
    text: str,
    index: int,
) -> GroundedScalar | None:
    if candidate.source_span is None or candidate.source_surface is None:
        return None

    start, end = candidate.source_span
    span = SourceSpan(candidate.source_surface, start, end)
    provenance = KernelProvenance(kind="problem_text", source_spans=(span,))
    hazards = tuple(
        KernelHazard(
            hazard_id=hid,
            category=hid,
            surface=candidate.surface,
            description=f"Scalar hazard {hid}",
        )
        for hid in candidate.hazards
    )
    return GroundedScalar(
        fact_id=f"scalar-{index:04d}",
        surface=candidate.surface,
        value=candidate.canonical,
        provenance=provenance,
        hazards=hazards,
    )


def _detect_question_target(text: str) -> QuestionTarget | None:
    text_lower = text.lower()
    if "how many" in text_lower:
        return QuestionTarget("how many", "count")
    if "how much" in text_lower:
        return QuestionTarget("how much", "quantity")
    if "?" in text:
        return QuestionTarget("?", "unknown")
    return None


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
_DECREASE_TO_FRACTION_RE = re.compile(
    r"(?P<transition>decrease\s+to)\s+(?P<fraction>\d+\s*/\s*\d+)\s+of",
    re.IGNORECASE,
)
_PERCENT_OF_PROPOSAL_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*%\s+of\b",
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
_ACTOR_VERB_RE = re.compile(
    r"\b(?P<actor>[A-Z][A-Za-z'-]*)\s+"
    r"(?:gave|gives|give|received|receives|spent|spends|ate|eats|bought|buys|sold|sells)\b"
)
_TRANSFER_RE = re.compile(
    r"\b(?P<agent>[A-Z][A-Za-z'-]*)\s+(?:gave|gives|give|handed|passed)\s+"
    r"(?P<patient>[A-Z][A-Za-z'-]*)\s+"
    r"(?P<quantity>\d+(?:\.\d+)?)\s+(?P<object>[A-Za-z][A-Za-z'-]*)",
)

_QUANTITY_ENTITY_PRONOUNS: frozenset[str] = frozenset({
    "he", "her", "hers", "him", "his", "it", "its", "one", "ones",
    "she", "their", "theirs", "them", "these", "they", "this", "those",
})

_QUANTITY_ENTITY_CONFUSER_SURFACES: tuple[str, ...] = (
    "each",
    "fewer than",
    "greater than",
    "less than",
    "more than",
    "per",
    "percent",
    "percentage",
    "ratio",
)


def _proportional_decrease_proposals(text: str) -> tuple[ConstructionProposal, ...]:
    """Propose the one authorized proposal-first construction from its chunk."""
    matches = tuple(_DECREASE_TO_FRACTION_RE.finditer(text))
    if len(matches) != 1:
        return ()
    match = matches[0]
    evidence = SourceSpan(
        text[match.start():match.end()],
        match.start(),
        match.end(),
    )
    return (
        propose_construction(
            "proportional_change.decrease_to_fraction",
            (evidence,),
        ),
    )


def _percent_partition_proposals(
    text: str,
    frames: tuple[ProcessFrame, ...],
) -> tuple[ConstructionProposal, ...]:
    """Propose percent partition from a process cue plus explicit percent-of."""
    frame_names = {frame.name for frame in frames}
    if not frame_names & {"partition", "consumption"}:
        return ()

    evidence_spans = tuple(
        SourceSpan(text[match.start():match.end()], match.start(), match.end())
        for match in _PERCENT_OF_PROPOSAL_RE.finditer(text)
    )
    if not evidence_spans:
        return ()

    return (
        propose_construction(
            "partition.percent_partition",
            evidence_spans,
        ),
    )


def _has_list_or_enumeration_suffix(text: str, end: int) -> bool:
    sentence_ends = tuple(
        index
        for marker in ".!?"
        if (index := text.find(marker, end)) != -1
    )
    sentence_end = min(sentence_ends, default=len(text))
    tail = text[end:sentence_end].lstrip().lower()
    return tail.startswith((",", ";", "and ", "or "))


def _quantity_entity_proposals(
    text: str,
    quantities: tuple[GroundedScalar, ...],
    frames: tuple[ProcessFrame, ...],
) -> tuple[ConstructionProposal, ...]:
    """Propose one narrow local quantity/entity cue from existing extraction.

    The family is intentionally unavailable when another process frame or a
    rate/comparison/percent surface is active.  Such text needs a different
    family to interpret it; this seam never selects the nearest noun.
    """

    if len(quantities) != 1 or frames:
        return ()
    if any(
        surface_in_text(surface, text)
        for surface in _QUANTITY_ENTITY_CONFUSER_SURFACES
    ):
        return ()

    matches = tuple(_ENTITY_AFTER_QUANTITY_RE.finditer(text))
    if len(matches) != 1:
        return ()
    match = matches[0]
    if "%" in match.group("quantity"):
        return ()
    if match.group("entity").lower() in _QUANTITY_ENTITY_PRONOUNS:
        return ()
    if _has_list_or_enumeration_suffix(text, match.end("entity")):
        return ()

    quantity_span = quantities[0].provenance.source_spans[0]
    if (
        quantity_span.start != match.start("quantity")
        or quantity_span.end != match.end("quantity")
    ):
        return ()

    evidence = SourceSpan(
        text[match.start():match.end()],
        match.start(),
        match.end(),
    )
    return (propose_construction("binding.quantity_entity", (evidence,)),)


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
            mention_id="", kind=kind, surface=text[start:end],
            span=SourceSpan(text[start:end], start, end), fact_id=fact_id,
        )

    for quantity in quantities:
        span = quantity.provenance.source_spans[0]
        add("quantity", span.start, span.end, fact_id=quantity.fact_id)
    for unit in units:
        span = unit.provenance.source_spans[0]
        add("unit", span.start, span.end, fact_id=unit.fact_id)
    for pattern in (_ENTITY_AFTER_QUANTITY_RE, _FRACTION_ENTITY_RE, _QUESTION_ENTITY_RE):
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
            mention_id=f"mention-{index:04d}", kind=m.kind, surface=m.surface,
            span=m.span, fact_id=m.fact_id,
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

    def bind(binding_type: str, source: GroundedMention, target: GroundedMention) -> None:
        key = (binding_type, source.mention_id, target.mention_id)
        if key in seen:
            return
        seen.add(key)
        bindings.append(MentionBinding(
            binding_id="", binding_type=binding_type,
            source_mention_id=source.mention_id, target_mention_id=target.mention_id,
            evidence_spans=(source.span, target.span),
        ))

    for pattern in (_ENTITY_AFTER_QUANTITY_RE, _FRACTION_ENTITY_RE):
        for match in pattern.finditer(text):
            entity = by_span_kind.get((match.start("entity"), match.end("entity"), "object"))
            if entity is None:
                continue
            candidates = [q for q in quantities if q.span.start == match.start("quantity")]
            if candidates:
                bind("quantity_entity", candidates[0], entity)
    units = [m for m in mentions if m.kind == "unit"]
    for quantity in quantities:
        following = [
            unit
            for unit in units
            if unit.span.start >= quantity.span.end
            and not text[quantity.span.end:unit.span.start].strip()
        ]
        if following:
            bind("quantity_unit", quantity, min(following, key=lambda u: u.span.start))

    ordered = sorted(bindings, key=lambda b: (b.evidence_spans[0].start, b.binding_type, b.target_mention_id))
    return tuple(MentionBinding(
        binding_id=f"binding-{index:04d}", binding_type=b.binding_type,
        source_mention_id=b.source_mention_id, target_mention_id=b.target_mention_id,
        evidence_spans=b.evidence_spans,
    ) for index, b in enumerate(ordered))


def _quantity_kind_dispositions(
    mentions: tuple[GroundedMention, ...],
    bindings: tuple[MentionBinding, ...],
) -> tuple[QuantityKindDisposition, ...]:
    """Close count/measurement kind only from existing local bindings."""

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

        bound_units = unit_bindings.get(quantity.mention_id, [])
        if not bound_units:
            dispositions.append(QuantityKindDisposition(
                quantity_mention_id=quantity.mention_id,
                entity_mention_id=entity.mention_id,
                quantity_kind="count",
                unit_mention_id=None,
                evidence_spans=binding.evidence_spans,
            ))
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
        dispositions.append(QuantityKindDisposition(
            quantity_mention_id=quantity.mention_id,
            entity_mention_id=entity.mention_id,
            quantity_kind="measurement",
            unit_mention_id=unit.mention_id,
            evidence_spans=tuple(evidence[key] for key in sorted(evidence)),
        ))

    return tuple(dispositions)


def _bound_relations(
    text: str,
    mentions: tuple[GroundedMention, ...],
    bindings: tuple[MentionBinding, ...],
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
                if mention.kind == part.kind and mention.surface.lower() == part.surface.lower()
            ),
            key=lambda mention: mention.span.start,
            default=part,
        )
        if "%" not in quantity.surface and quantity.surface.lower() not in {"half", "third", "quarter"}:
            continue
        roles = [
            BoundRole("part", canonical_part.mention_id, canonical_part.kind, (canonical_part.span,)),
            BoundRole("scale", quantity.mention_id, quantity.kind, (quantity.span,)),
        ]
        if whole is not None:
            whole_entity = by_id[whole.target_mention_id]
            roles.insert(0, BoundRole("whole", whole_entity.mention_id, whole_entity.kind, (whole_entity.span,)))
        relation_type = "percent_of" if "%" in quantity.surface else "subgroup_partition"
        relations.append(BoundRelation(
            relation_id="", relation_type=relation_type, roles=tuple(roles),
            evidence_spans=tuple(span for role in roles for span in role.evidence_spans),
        ))

    for match in _COPULAR_PARTITION_RE.finditer(text):
        quantity = next((m for m in mentions if m.kind == "quantity" and m.span.start == match.start("quantity")), None)
        whole = next((m for m in mentions if m.kind == "object" and m.span.start == match.start("whole")), None)
        part = next((m for m in mentions if m.kind == "object" and m.span.start == match.start("part")), None)
        if quantity is None or whole is None or part is None:
            continue
        canonical_whole = min(
            (
                mention
                for mention in mentions
                if mention.kind == "object" and mention.surface.lower() == whole.surface.lower()
            ),
            key=lambda mention: mention.span.start,
            default=whole,
        )
        roles = (
            BoundRole("whole", canonical_whole.mention_id, canonical_whole.kind, (canonical_whole.span,)),
            BoundRole("part", part.mention_id, part.kind, (part.span,)),
            BoundRole("scale", quantity.mention_id, quantity.kind, (quantity.span,)),
        )
        relations.append(BoundRelation(
            relation_id="",
            relation_type="subgroup_partition",
            roles=roles,
            evidence_spans=(quantity.span, canonical_whole.span, part.span),
        ))

    decrease_matches = list(_DECREASE_TO_FRACTION_RE.finditer(text))
    if len(decrease_matches) == 1:
        match = decrease_matches[0]
        scale = next((m for m in mentions if m.kind == "quantity" and m.span.start == match.start("fraction")), None)
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
                    m for m in mentions
                    if m.kind == "object" and state_match is not None and m.span.start == state_match.start("state")
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
                    (SourceSpan(text[match.start("transition"):match.end("transition")], match.start("transition"), match.end("transition")),),
                ),
            ]
            if base_unit_binding is not None:
                unit = by_id.get(base_unit_binding.target_mention_id)
                if unit is not None:
                    roles.append(BoundRole("unit", unit.mention_id, unit.kind, (unit.span,)))
            relations.append(BoundRelation(
                relation_id="",
                relation_type="decrease_to_fraction",
                roles=tuple(roles),
                evidence_spans=tuple(span for role in roles for span in role.evidence_spans),
            ))

    for match in _TRANSFER_RE.finditer(text):
        def at(group: str, kind: str) -> GroundedMention | None:
            return next((m for m in mentions if m.kind == kind and m.span.start == match.start(group)), None)
        agent = at("agent", "actor")
        patient = at("patient", "actor")
        quantity = at("quantity", "quantity")
        obj = at("object", "object")
        if all((agent, patient, quantity, obj)):
            assert agent and patient and quantity and obj
            roles = tuple(
                BoundRole(name, mention.mention_id, mention.kind, (mention.span,))
                for name, mention in (
                    ("agent", agent), ("patient", patient),
                    ("quantity", quantity), ("object", obj),
                )
            )
            relations.append(BoundRelation(
                "", "transfer", roles,
                tuple(m.span for m in (agent, patient, quantity, obj)),
            ))

    relations.sort(key=lambda r: (r.evidence_spans[0].start, r.relation_type))
    return tuple(
        BoundRelation(
            f"bound-rel-{index:04d}", relation.relation_type,
            relation.roles, relation.evidence_spans,
        )
        for index, relation in enumerate(relations)
    )


def _bound_question_target(text: str, mentions: tuple[GroundedMention, ...]) -> BoundQuestionTarget | None:
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
                m for m in mentions
                if m.kind == "object" and m.surface.lower() == entity_surface.lower()
            ),
            None,
        )
        span = SourceSpan(text[decrease_delta.start():decrease_delta.end()], decrease_delta.start(), decrease_delta.end())
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
            "unknown", "?", None, "unresolved",
            (SourceSpan("?", qmark, qmark + 1),),
            target_operator="unknown",
            target_state="unknown",
            target_direction="unknown",
        )
    entity = next((m for m in mentions if m.kind == "object" and m.span.start == question.start("entity")), None)
    question_clause = text[question.start():]
    prefix = text[max(0, question.start() - 32):question.end()].lower()
    question_lower = question_clause.lower()
    if "more" in question.group(0).lower():
        target_type = "difference"
        target_operator = "difference"
        target_state = "delta"
        target_direction = "unknown"
        unknown_slot = "difference"
    elif any(x in question_lower for x in ("were in", "was in", "started with", "originally")):
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
    span = SourceSpan(text[question.start():question.end()], question.start(), question.end())
    return BoundQuestionTarget(
        target_type, question.group("entity"),
        entity.mention_id if entity else None, unknown_slot, (span,),
        target_operator=target_operator,
        target_state=target_state,
        target_direction=target_direction,
    )


def build_problem_frame(problem_text: str) -> ProblemFrame:
    """Build a substrate-backed ProblemFrame from raw problem text.

    Deterministic ordering; preserves hazards and provenance; does not derive
    answers or bind case-specific behavior.
    """
    builder = ProblemFrameBuilder()
    builder.set_problem_text(problem_text)

    scalars = _filter_scalar_candidates(problem_text, extract_scalar_candidates(problem_text))
    for scalar in scalars:
        builder.add_scalar(scalar)

    grounded_quantities: list[GroundedScalar] = []
    for index, scalar in enumerate(scalars):
        grounded = _scalar_to_grounded(scalar, problem_text, index)
        if grounded is not None:
            builder.add_quantity(grounded)
            grounded_quantities.append(grounded)

    units = _extract_unit_candidates(problem_text)
    for unit in units:
        builder.add_unit(unit)

    for hazard in _extract_hazards(problem_text):
        builder.add_hazard(hazard)

    frames = _extract_process_frame_candidates(problem_text)
    for frame in frames:
        builder.add_process_frame(frame)

    for relation in _extract_candidate_relations(problem_text, frames):
        builder.add_relation(relation)

    question_target = _detect_question_target(problem_text)
    if question_target is not None:
        builder.set_question_target(question_target)

    # ADR-0223/0224: surface/process evidence proposes catalog constructions
    # before role binding and ContractAssessment.  Proposals remain diagnostic
    # hypotheses; bound relations ground and organ contracts determine.
    for proposal in _proportional_decrease_proposals(problem_text):
        builder.add_proposal(proposal)
    for proposal in _percent_partition_proposals(problem_text, frames):
        builder.add_proposal(proposal)
    for proposal in _quantity_entity_proposals(
        problem_text,
        tuple(grounded_quantities),
        frames,
    ):
        builder.add_proposal(proposal)

    mentions = _extract_mentions(problem_text, tuple(grounded_quantities), units)
    bindings = _extract_bindings(problem_text, mentions)
    for mention in mentions:
        builder.add_mention(mention)
        if mention.kind == "actor":
            builder.add_actor(mention.surface)
        elif mention.kind == "object":
            builder.add_object(mention.surface)
    for binding in bindings:
        builder.add_binding(binding)
    for disposition in _quantity_kind_dispositions(mentions, bindings):
        builder.add_quantity_kind_disposition(disposition)
    for relation in _bound_relations(problem_text, mentions, bindings):
        builder.add_bound_relation(relation)
    bound_target = _bound_question_target(problem_text, mentions)
    if bound_target is not None:
        builder.set_bound_question_target(bound_target)

    initial_frame = builder.build()

    from generate.problem_frame_contracts import assess_contracts, get_contract_family_id
    from generate.construction_affordances import make_proposal

    assessments = assess_contracts(initial_frame)
    proposals = list(initial_frame.proposals)
    proposed_family_ids = {proposal.family_id for proposal in proposals}
    for assessment in assessments:
        family_id = get_contract_family_id(assessment.candidate_organ)
        if family_id is not None and family_id not in proposed_family_ids:
            proposal = make_proposal(
                family_id=family_id,
                evidence_spans=assessment.evidence_spans,
                assessment_runnable=assessment.runnable,
                missing_roles=assessment.missing_bindings,
                active_hazards=assessment.unresolved_hazards,
            )
            proposals.append(proposal)
            proposed_family_ids.add(family_id)

    return dataclasses.replace(initial_frame, proposals=tuple(proposals))



def recognized_scalar_surfaces(frame: ProblemFrame) -> tuple[str, ...]:
    """Return sorted scalar surfaces recognized in a ProblemFrame."""
    surfaces = {s.surface for s in frame.scalars}
    surfaces.update(q.surface for q in frame.quantities)
    return tuple(sorted(surfaces))


def recognized_unit_surfaces(frame: ProblemFrame) -> tuple[str, ...]:
    """Return sorted unit surfaces recognized in a ProblemFrame."""
    return tuple(sorted({u.surface for u in frame.units}))


def recognized_process_frame_names(frame: ProblemFrame) -> tuple[str, ...]:
    """Return sorted process-frame names attached as candidates."""
    return tuple(sorted({f.name for f in frame.process_frames}))


def recognized_hazard_ids(frame: ProblemFrame) -> tuple[str, ...]:
    """Return sorted hazard IDs preserved on the frame."""
    return tuple(sorted({h.hazard_id for h in frame.hazards}))


def scalar_canonical_values(frame: ProblemFrame) -> tuple[Fraction, ...]:
    """Return canonical scalar values in deterministic order."""
    values = [s.canonical for s in frame.scalars]
    values.extend(q.value for q in frame.quantities)
    return tuple(sorted(values, key=lambda v: (v.denominator, v.numerator)))
