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
from generate.problem_frame import ProblemFrame, ProblemFrameBuilder, QuestionTarget
from generate.process_frames import ProcessFrame, all_frames, lookup_frame
from language_packs.ambiguity_hazards import (
    AmbiguityHazard,
    all_registered_surfaces,
    lookup_hazards,
)
from language_packs.scalar_equivalence import (
    ScalarCandidate,
    extract_scalar_candidates,
    list_unsupported_surfaces,
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


def _surface_in_text(surface: str, text_lower: str) -> bool:
    token = surface.lower()
    padded = f" {text_lower} "
    return (
        f" {token} " in padded
        or text_lower.startswith(f"{token} ")
        or text_lower.endswith(f" {token}")
        or text_lower == token
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

    return tuple(sorted(units, key=lambda u: (u.provenance.source_spans[0].start, u.surface)))


def _extract_hazards(text: str) -> tuple[KernelHazard, ...]:
    text_lower = text.lower()
    hazards: list[KernelHazard] = []
    seen: set[str] = set()

    for surface in all_registered_surfaces():
        if not _surface_in_text(surface, text_lower):
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
    text_lower = text.lower()
    trigger_lower = trigger.lower()
    idx = text_lower.find(trigger_lower)
    if idx < 0:
        return None
    return SourceSpan(text[idx:idx + len(trigger_lower)], idx, idx + len(trigger_lower))


def _extract_process_frame_candidates(text: str) -> tuple[ProcessFrame, ...]:
    text_lower = text.lower()
    matched: dict[str, ProcessFrame] = {}

    for frame in all_frames():
        for trigger in frame.trigger_surfaces:
            if _surface_in_text(trigger, text_lower):
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


def _has_unsupported_scalar_surface(text: str) -> bool:
    for surface in list_unsupported_surfaces():
        if surface in text:
            return True
    return False


def build_problem_frame(problem_text: str) -> ProblemFrame:
    """Build a substrate-backed ProblemFrame from raw problem text.

    Deterministic ordering; preserves hazards and provenance; does not derive
    answers or bind case-specific behavior.
    """
    builder = ProblemFrameBuilder()

    scalars = _filter_scalar_candidates(problem_text, extract_scalar_candidates(problem_text))
    for scalar in scalars:
        builder.add_scalar(scalar)

    for index, scalar in enumerate(scalars):
        grounded = _scalar_to_grounded(scalar, problem_text, index)
        if grounded is not None:
            builder.add_quantity(grounded)

    for unit in _extract_unit_candidates(problem_text):
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

    # Unsupported scalar tokenisations remain absent from scalars; callers can
    # consult list_unsupported_surfaces() — we do not broaden ADR-0128 here.
    _ = _has_unsupported_scalar_surface(problem_text)

    return builder.build()


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