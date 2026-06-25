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

from fractions import Fraction

from generate.kernel_facts import GroundedScalar
from generate.problem_frame import GroundedUnaryDeltaCue, ProblemFrame, ProblemFrameBuilder
from generate.problem_frame_bound_relations import (
    _bound_question_target,
    _bound_relations,
    _quantity_kind_dispositions,
)
from generate.problem_frame_extractors import (
    _detect_question_target,
    _extract_candidate_relations,
    _extract_hazards,
    _extract_process_frame_candidates,
    _extract_unit_candidates,
    _filter_scalar_candidates,
    _scalar_to_grounded,
)
from generate.problem_frame_mentions import _extract_bindings, _extract_mentions
from generate.problem_frame_proposals import (
    _percent_partition_proposals,
    _proportional_decrease_proposals,
    _quantity_entity_proposals,
    _unary_delta_proposals,
)
from language_packs.scalar_equivalence import extract_scalar_candidates


def build_problem_frame(problem_text: str) -> ProblemFrame:
    """Build a substrate-backed ProblemFrame from raw problem text.

    Deterministic ordering; preserves hazards and provenance; does not derive
    answers or bind case-specific behavior.
    """
    builder = ProblemFrameBuilder()
    builder.set_problem_text(problem_text)

    scalars = _filter_scalar_candidates(
        problem_text, extract_scalar_candidates(problem_text)
    )
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
    quantity_entity_proposals = _quantity_entity_proposals(
        problem_text,
        tuple(grounded_quantities),
        frames,
    )
    for proposal in quantity_entity_proposals:
        builder.add_proposal(proposal)
    unary_delta_proposals = _unary_delta_proposals(problem_text)
    for proposal in unary_delta_proposals:
        builder.add_proposal(proposal)
        for span in proposal.evidence_spans:
            surface = span.text
            if surface in {"gained", "lost"}:
                action_kind = "gain" if surface == "gained" else "loss"
                direction = "increase" if surface == "gained" else "decrease"
                cue = GroundedUnaryDeltaCue(
                    cue_id=f"cue-{builder.unary_delta_cue_count:04d}",
                    surface=surface,
                    action_kind=action_kind,
                    direction=direction,
                    span=span,
                )
                builder.add_unary_delta_cue(cue)

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

    proposals_for_grounding = (*quantity_entity_proposals, *unary_delta_proposals)
    for disposition in _quantity_kind_dispositions(
        problem_text,
        mentions,
        bindings,
        proposals_for_grounding,
    ):
        builder.add_quantity_kind_disposition(disposition)
    for relation in _bound_relations(
        problem_text,
        mentions,
        bindings,
        proposals_for_grounding,
        builder.unary_delta_cues,
    ):
        builder.add_bound_relation(relation)
    bound_target = _bound_question_target(problem_text, mentions)
    if bound_target is not None:
        builder.set_bound_question_target(bound_target)

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
