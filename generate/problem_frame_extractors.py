"""ProblemFrame extraction helpers — Phase 1 of the ADR-0236 builder split.

Owns all observation/extraction logic that surfaces raw facts from problem text.
This module has no dependency on ContractAssessment, make_proposal, or
ProblemFrameBuilder.
"""

from __future__ import annotations

import re
from fractions import Fraction

from generate.kernel_facts import (
    CandidateRelation,
    GroundedScalar,
    GroundedUnit,
    KernelHazard,
    KernelProvenance,
    RelationRole,
    SourceSpan,
)
from generate.problem_frame import QuestionTarget
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

_UNIT_STOPWORDS: frozenset[str] = frozenset(
    {
        "more",
        "less",
        "times",
        "percent",
        "percentage",
        "of",
        "and",
        "or",
        "the",
        "a",
        "an",
        "in",
        "to",
        "for",
        "with",
        "at",
        "by",
        "from",
        "each",
        "per",
        "way",
        "ways",
    }
)

_ORDINAL_SUFFIX_RE: re.Pattern[str] = re.compile(
    r"\b(half|third|quarter)\s+(place|position|grade|rank)\b",
    re.IGNORECASE,
)


def surface_in_text(surface: str, text: str) -> bool:
    """Match a registered surface at lexical, including punctuation, boundaries."""
    return (
        re.search(
            rf"(?<![\w]){re.escape(surface)}(?![\w])",
            text,
            flags=re.IGNORECASE,
        )
        is not None
    )


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

    return tuple(
        sorted(units, key=lambda u: (u.provenance.source_spans[0].start, u.surface))
    )


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
    return SourceSpan(text[match.start() : match.end()], match.start(), match.end())


def _sentence_contains_current_or_now(text: str, index: int) -> bool:
    start = max(
        text.rfind(".", 0, index),
        text.rfind("?", 0, index),
        text.rfind("!", 0, index),
    )
    end_candidates = [
        pos
        for pos in (
            text.find(".", index),
            text.find("?", index),
            text.find("!", index),
        )
        if pos != -1
    ]
    end = min(end_candidates) if end_candidates else len(text)
    sentence = text[start + 1 : end].lower()
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
