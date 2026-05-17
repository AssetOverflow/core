"""Tests for the Formation Pipeline artifact dataclasses (Phase 1)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from formation.candidate import (
    CandidateState,
    ConceptCandidate,
    CounterCandidate,
    OrderingHint,
    RelationCandidate,
    SourceRef,
)
from formation.course import (
    SCHEMA_VERSION,
    CourseYAML,
    FormationPlan,
    GateMeasurement,
    MasteryReport,
    OreBundle,
    OreEntry,
    PlanStep,
    SubjectSpec,
    ValidatedTripleSet,
)


def _source() -> SourceRef:
    return SourceRef(
        source_sha="a" * 64,
        span="...example span...",
        adapter="wikipedia",
        retrieved_at="2026-05-16T00:00:00Z",
    )


class TestImmutability:
    def test_subject_spec_frozen(self) -> None:
        spec = SubjectSpec(subject_id="x", title="t", target_depth="introductory")
        with pytest.raises(FrozenInstanceError):
            spec.subject_id = "y"  # type: ignore[misc]

    def test_relation_candidate_frozen(self) -> None:
        cand = RelationCandidate("h", "is", "t", (_source(),))
        with pytest.raises(FrozenInstanceError):
            cand.head = "x"  # type: ignore[misc]


class TestDefaults:
    def test_candidate_default_state_is_proposed(self) -> None:
        cand = RelationCandidate("wisdom", "is", "judgment", (_source(),))
        assert cand.state is CandidateState.PROPOSED
        assert cand.rejection_reason == ""

    def test_subject_spec_schema_version(self) -> None:
        spec = SubjectSpec(subject_id="x", title="t", target_depth="introductory")
        assert spec.schema_version == SCHEMA_VERSION

    def test_mastery_report_defaults_unsealed(self) -> None:
        report = MasteryReport(
            course_id="c.v1",
            source_bundle_sha="0" * 64,
            validated_set_sha="0" * 64,
            course_sha256="0" * 64,
            plan_sha256="0" * 64,
            gates=(),
            trace_hashes=(),
            ratified=False,
        )
        assert report.report_sha256 == ""
        assert report.failure_reasons == ()


class TestConstruction:
    def test_ore_bundle_round_trips(self) -> None:
        entry = OreEntry(
            source_sha="b" * 64,
            url="https://example.org/x",
            adapter="wikipedia",
            retrieved_at="2026-05-16T00:00:00Z",
            byte_length=128,
        )
        bundle = OreBundle(subject_id="subject.x", entries=(entry,))
        assert bundle.entries[0].source_sha == "b" * 64

    def test_validated_set_carries_quarantined(self) -> None:
        good = RelationCandidate(
            "wisdom", "is", "judgment", (_source(),), state=CandidateState.VALIDATED,
        )
        bad = RelationCandidate(
            "x", "is", "y", (_source(),),
            state=CandidateState.QUARANTINED,
            rejection_reason="identity_axis_collision",
        )
        vts = ValidatedTripleSet(
            subject_id="subject.x",
            concepts=(),
            relations=(good,),
            counters=(),
            ordering_hints=(),
            quarantined=(bad,),
        )
        assert vts.relations[0].state is CandidateState.VALIDATED
        assert vts.quarantined[0].rejection_reason == "identity_axis_collision"

    def test_course_yaml_construction(self) -> None:
        course = CourseYAML(
            course_id="x.v1",
            yaml_bytes=b"course:\n  id: x.v1\n",
            course_sha256="c" * 64,
            source_bundle_sha="d" * 64,
            validated_set_sha="e" * 64,
            template_id="definition",
            template_version="1.0.0",
        )
        assert course.template_id == "definition"

    def test_formation_plan_step_payload(self) -> None:
        step = PlanStep(step_type="seed_concept", payload={"term": "wisdom"})
        plan = FormationPlan(
            course_id="x.v1",
            course_sha256="c" * 64,
            steps=(step,),
            plan_sha256="p" * 64,
        )
        assert plan.steps[0].step_type == "seed_concept"

    def test_gate_measurement_strings(self) -> None:
        gate = GateMeasurement(
            name="replay_determinism", passed=True, measurement="1.0", threshold="1.0",
        )
        assert gate.passed is True


class TestOrderingHint:
    def test_ordering_hint_minimal(self) -> None:
        hint = OrderingHint(before="number", after="addition")
        assert hint.sources == ()


class TestConceptCounterCandidate:
    def test_concept_candidate_state(self) -> None:
        cc = ConceptCandidate(
            canonical_term="wisdom",
            definition="judgment grounded in experience",
            sources=(_source(),),
        )
        assert cc.state is CandidateState.PROPOSED

    def test_counter_candidate_construction(self) -> None:
        counter = CounterCandidate(
            head="addition", relation="is", tail="non-commutative", sources=(_source(),),
        )
        assert counter.head == "addition"
