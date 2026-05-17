"""Tests for ``formation.compiler`` and ``formation.runner`` — Phase 4."""

from __future__ import annotations

import pytest

from formation.candidate import (
    CandidateState,
    ConceptCandidate,
    CounterCandidate,
    RelationCandidate,
    SourceRef,
)
from formation.compiler import compile_course
from formation.compose import compose
from formation.course import (
    CourseYAML,
    FormationPlan,
    PlanStep,
    SubjectSpec,
    ValidatedTripleSet,
)
from formation.runner import (
    PipelineCallable,
    RunnerHalt,
    TurnObservation,
    VERSOR_HALT_THRESHOLD,
    run_plan,
)


def _src() -> SourceRef:
    return SourceRef(
        source_sha="a" * 64,
        span="span",
        adapter="wikipedia",
        retrieved_at="2026-05-16T00:00:00Z",
    )


def _spec() -> SubjectSpec:
    return SubjectSpec(
        subject_id="subject.x", title="Subject X", target_depth="introductory",
    )


def _validated_set() -> ValidatedTripleSet:
    concepts = (
        ConceptCandidate(
            canonical_term="wisdom",
            definition="judgment grounded in experience",
            sources=(_src(),),
            state=CandidateState.VALIDATED,
        ),
        ConceptCandidate(
            canonical_term="judgment",
            definition="reasoned decision",
            sources=(_src(),),
            state=CandidateState.VALIDATED,
        ),
    )
    relations = (
        RelationCandidate(
            head="wisdom", relation="is", tail="judgment",
            sources=(_src(),), state=CandidateState.VALIDATED,
        ),
    )
    counters = (
        CounterCandidate(
            head="wisdom", relation="is", tail="folly",
            sources=(_src(),), state=CandidateState.VALIDATED,
        ),
    )
    return ValidatedTripleSet(
        subject_id="subject.x",
        concepts=concepts,
        relations=relations,
        counters=counters,
        ordering_hints=(),
    )


def _course() -> CourseYAML:
    return compose(
        validated_set=_validated_set(),
        spec=_spec(),
        source_bundle_sha="0" * 64,
    )


# ---------- compiler ----------


class TestCompile:
    def test_plan_is_deterministic(self) -> None:
        course = _course()
        p1 = compile_course(course)
        p2 = compile_course(course)
        assert p1.plan_sha256 == p2.plan_sha256
        assert p1.steps == p2.steps

    def test_plan_carries_course_sha(self) -> None:
        course = _course()
        plan = compile_course(course)
        assert plan.course_sha256 == course.course_sha256
        assert plan.course_id == course.course_id

    def test_seeds_concepts(self) -> None:
        plan = compile_course(_course())
        seeds = [s for s in plan.steps if s.step_type == "seed_concept"]
        assert len(seeds) >= 2  # wisdom + judgment
        assert any(s.payload.get("canonical_term") == "wisdom" for s in seeds)

    def test_introduces_relation(self) -> None:
        plan = compile_course(_course())
        intros = [s for s in plan.steps if s.step_type == "introduce_relation"]
        assert any(
            s.payload.get("head") == "wisdom"
            and s.payload.get("relation") == "is"
            and s.payload.get("tail") == "judgment"
            for s in intros
        )

    def test_walks_phase3(self) -> None:
        plan = compile_course(_course())
        walks = [s for s in plan.steps if s.step_type == "walk_step"]
        assert len(walks) >= 1

    def test_adversarial_probes_present(self) -> None:
        plan = compile_course(_course())
        probes = [s for s in plan.steps if s.step_type == "adversarial_probe"]
        assert len(probes) >= 1

    def test_replay_assertion(self) -> None:
        plan = compile_course(_course())
        replays = [s for s in plan.steps if s.step_type == "replay_assertion"]
        assert len(replays) == 1

    def test_invalid_yaml_rejected(self) -> None:
        bad = CourseYAML(
            course_id="x", yaml_bytes=b"not a mapping",
            course_sha256="0" * 64, source_bundle_sha="0" * 64,
            validated_set_sha="0" * 64, template_id="definition",
            template_version="1.0.0",
        )
        with pytest.raises(ValueError):
            compile_course(bad)


# ---------- runner ----------


def _ok_pipeline(step: PlanStep) -> TurnObservation:
    # Adversarial probes must be rejected; legit steps accepted.
    accepted = step.step_type != "adversarial_probe"
    return TurnObservation(
        trace_hash=f"trace:{step.step_type}:{step.payload.get('head','')}:{step.payload.get('relation','')}:{step.payload.get('tail','')}",
        versor_condition=0.0,
        accepted=accepted,
        has_provenance=True,
    )


class TestRunner:
    def test_run_produces_one_result_per_step(self) -> None:
        plan = compile_course(_course())
        out = run_plan(plan, _ok_pipeline)
        assert out.halted is False
        assert len(out.results) == len(plan.steps)

    def test_run_is_deterministic_under_deterministic_pipeline(self) -> None:
        plan = compile_course(_course())
        a = run_plan(plan, _ok_pipeline)
        b = run_plan(plan, _ok_pipeline)
        assert tuple(r.trace_hash for r in a.results) == tuple(r.trace_hash for r in b.results)

    def test_halts_on_versor_violation(self) -> None:
        plan = compile_course(_course())

        def bad_pipeline(step: PlanStep) -> TurnObservation:
            return TurnObservation(
                trace_hash="t", versor_condition=1.0e-3, accepted=True, has_provenance=True,
            )
        out = run_plan(plan, bad_pipeline)
        assert out.halted is True
        assert out.halt_step_index == 0

    def test_halt_threshold_exact_boundary(self) -> None:
        plan = compile_course(_course())

        def boundary(step: PlanStep) -> TurnObservation:
            return TurnObservation(
                trace_hash="t",
                versor_condition=VERSOR_HALT_THRESHOLD,  # exactly the threshold -> halt
                accepted=True, has_provenance=True,
            )
        out = run_plan(plan, boundary)
        assert out.halted is True

    def test_just_under_threshold_does_not_halt(self) -> None:
        plan = compile_course(_course())

        def near(step: PlanStep) -> TurnObservation:
            return TurnObservation(
                trace_hash="t",
                versor_condition=VERSOR_HALT_THRESHOLD / 10,
                accepted=True, has_provenance=True,
            )
        out = run_plan(plan, near)
        assert out.halted is False

    def test_step_result_provenance_propagates(self) -> None:
        plan = compile_course(_course())

        def no_prov(step: PlanStep) -> TurnObservation:
            return TurnObservation(
                trace_hash=f"t:{id(step)}", versor_condition=0.0,
                accepted=True, has_provenance=False,
            )
        out = run_plan(plan, no_prov)
        assert all(r.has_provenance is False for r in out.results)
