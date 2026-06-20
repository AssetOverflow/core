"""Tests for generate/problem_frame.py."""
from __future__ import annotations

from fractions import Fraction
import pytest

from generate.problem_frame import BoundQuestionTarget, ProblemFrame, ProblemFrameBuilder, QuestionTarget
from generate.kernel_facts import (
    SourceSpan,
    KernelProvenance,
    KernelHazard,
    GroundedScalar,
    GroundedUnit,
    RelationRole,
    CandidateRelation,
)
from language_packs.scalar_equivalence import ScalarCandidate
from generate.process_frames import frame_by_name


def test_question_target_validation() -> None:
    # Valid targets
    target = QuestionTarget("how many apples", "count", "apple")
    assert target.surface == "how many apples"
    assert target.target_type == "count"
    assert target.unit == "apple"

    # Invalid type
    with pytest.raises(ValueError, match="must be one of"):
        QuestionTarget("target", "invalid_type")


def test_bound_question_target_rejects_illegal_delta_combinations() -> None:
    span = SourceSpan("what will the temperature decrease by?", 0, 37)

    with pytest.raises(ValueError, match="difference targets must bind a delta target_state"):
        BoundQuestionTarget(
            "difference",
            "temperature",
            "mention-0001",
            "delta_quantity",
            (span,),
            target_operator="difference",
            target_state="final",
            target_direction="decrease",
        )


def test_empty_problem_frame() -> None:
    builder = ProblemFrameBuilder()
    frame = builder.build()

    assert len(frame.quantities) == 0
    assert len(frame.scalars) == 0
    assert len(frame.units) == 0
    assert len(frame.actors) == 0
    assert len(frame.objects) == 0
    assert len(frame.candidate_relations) == 0
    assert len(frame.process_frames) == 0
    assert frame.question_target is None
    assert len(frame.hazards) == 0
    assert len(frame.provenance) == 0


def test_mixed_problem_frame_builder() -> None:
    builder = ProblemFrameBuilder()

    # Add actors and objects
    builder.add_actor("John")
    builder.add_object("apple")

    # Primitives for scalar
    span = SourceSpan("half", 0, 4)
    prov_text = KernelProvenance(kind="problem_text", source_spans=(span,))
    hazard = KernelHazard("haz-1", "unbound_base_quantity", "half", "unbound")
    scalar = GroundedScalar("fact-1", "half", Fraction(1, 2), prov_text, (hazard,))

    builder.add_quantity(scalar)

    # Scalar facade candidate
    scal_cand = ScalarCandidate("0.5", Fraction(1, 2), "decimal", None, ())
    builder.add_scalar(scal_cand)

    # Grounded unit
    prov_unit = KernelProvenance(kind="kernel_unit")
    unit = GroundedUnit("fact-2", "dollar", "money", "dollar", prov_unit)
    builder.add_unit(unit)

    # Process frame
    proc_frame = frame_by_name("transfer")
    assert proc_frame is not None
    builder.add_process_frame(proc_frame)

    # Relation
    role = RelationRole("agent", True, "The agent")
    rel = CandidateRelation("rel-1", "transfer", (role,), prov_text, (hazard,))
    builder.add_relation(rel)

    # Question target
    q_target = QuestionTarget("how many", "quantity", "dollar")
    builder.set_question_target(q_target)

    # Direct hazard/provenance
    prov_spec = KernelProvenance(kind="speculative")
    builder.add_provenance(prov_spec)
    builder.add_hazard(hazard)

    # Build and verify
    frame = builder.build()

    assert frame.actors == ("John",)
    assert frame.objects == ("apple",)
    assert frame.quantities == (scalar,)
    assert frame.scalars == (scal_cand,)
    assert frame.units == (unit,)
    assert frame.process_frames == (proc_frame,)
    assert frame.candidate_relations == (rel,)
    assert frame.question_target == q_target

    # Verify hazards collected (scalar.hazards + rel.hazards + direct hazard)
    assert hazard in frame.hazards
    assert len(frame.hazards) >= 3

    # Verify provenance collected (scalar.prov + unit.prov + rel.prov + direct prov_spec + rel.prov)
    assert prov_text in frame.provenance
    assert prov_unit in frame.provenance
    assert prov_spec in frame.provenance
    assert len(frame.provenance) >= 4


def test_immutability() -> None:
    builder = ProblemFrameBuilder()
    frame = builder.build()

    with pytest.raises(AttributeError):
        frame.quantities = ()  # type: ignore
