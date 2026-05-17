"""End-to-end micro-course (Phase 6).

Drives a hand-curated input through Forge -> Compose -> Compile -> Run ->
Ratify -> Promote with a stub pipeline, asserting that the back half of the
Formation Pipeline produces a Ratified ``MasteryReport`` and a successful
promotion that lands the course in the ``MasteredCoursesIndex``.

This is the smallest test that exercises every trust boundary except
Mining/Smelting (which are exercised separately in ``test_smelter.py``).
"""

from __future__ import annotations

from formation.allowlist import AllowedSource, SourceAllowlist
from formation.candidate import (
    ConceptCandidate,
    CounterCandidate,
    RelationCandidate,
    SourceRef,
)
from formation.compiler import compile_course
from formation.compose import compose
from formation.course import PlanStep, SubjectSpec
from formation.forge import Forge
from formation.index import MasteredCoursesIndex
from formation.mastery import verify_report
from formation.promote import promote
from formation.ratify import ratify
from formation.runner import TurnObservation, run_plan


_PRIMARY = "1" * 64


def _src() -> SourceRef:
    return SourceRef(
        source_sha=_PRIMARY, span="example span", adapter="wikipedia",
        retrieved_at="2026-05-16T00:00:00Z",
    )


def _stub_pipeline(step: PlanStep) -> TurnObservation:
    """A deterministic stub pipeline.

    Adversarial probes are rejected (``accepted=False``); legitimate steps
    are accepted.  Trace hashes are derived from the step payload so a
    second run produces identical hashes.
    """
    accepted = step.step_type != "adversarial_probe"
    keyed = (
        step.step_type,
        step.payload.get("canonical_term", ""),
        step.payload.get("head", ""),
        step.payload.get("relation", ""),
        step.payload.get("tail", ""),
        step.payload.get("probe_id", ""),
    )
    return TurnObservation(
        trace_hash=f"trace:{':'.join(str(k) for k in keyed)}",
        versor_condition=0.0,
        accepted=accepted,
        has_provenance=True,
    )


def _build_validated_set(forge: Forge):
    src = _src()
    concepts = [
        ConceptCandidate(
            canonical_term=name, definition=f"definition of {name}", sources=(src,),
        )
        for name in (
            "wisdom", "judgment", "experience", "number", "quantity",
        )
    ]
    relation_pairs = [
        ("wisdom", "is", "judgment"),
        ("judgment", "is", "experience"),
        ("number", "is", "quantity"),
        ("quantity", "is", "magnitude"),
        ("magnitude", "is", "measure"),
        ("wisdom", "produces", "judgment"),
        ("number", "produces", "quantity"),
        ("experience", "grounds", "wisdom"),
        ("measure", "grounds", "quantity"),
        ("judgment", "follows", "experience"),
    ]
    relations = [
        RelationCandidate(head=h, relation=r, tail=t, sources=(src,))
        for h, r, t in relation_pairs
    ]
    counters = [
        CounterCandidate(head="wisdom", relation="is", tail="folly", sources=(src,)),
        CounterCandidate(head="number", relation="is", tail="opinion", sources=(src,)),
    ]
    return forge.validate(
        "subject.micro",
        concepts=concepts,
        relations=relations,
        counters=counters,
    )


def test_micro_course_ratifies_and_promotes(tmp_path) -> None:
    # 1. Forge.
    allowlist = SourceAllowlist((
        AllowedSource(_PRIMARY, "primary", "stanford-textbook"),
    ))
    forge = Forge(allowlist=allowlist)
    validated = _build_validated_set(forge)
    assert len(validated.relations) == 10  # all ten triples accepted
    assert len(validated.concepts) == 5

    # 2. Compose.
    spec = SubjectSpec(
        subject_id="subject.micro",
        title="Micro Course",
        target_depth="introductory",
    )
    course = compose(
        validated_set=validated,
        spec=spec,
        source_bundle_sha="0" * 64,
    )
    assert course.course_sha256 != ""
    assert len(course.yaml_bytes) > 0

    # 3. Compile.
    plan = compile_course(course)
    assert plan.plan_sha256 != ""
    # Plan must include every Phase II relation as a walk_step.
    walks = [s for s in plan.steps if s.step_type == "walk_step"]
    walked_triples = {
        (s.payload["head"], s.payload["relation"], s.payload["tail"]) for s in walks
    }
    expected = {(r.head, r.relation, r.tail) for r in validated.relations}
    assert expected <= walked_triples

    # 4. Run (twice, for the determinism gate).
    first = run_plan(plan, _stub_pipeline)
    second = run_plan(plan, _stub_pipeline)
    assert first.halted is False
    assert second.halted is False
    assert tuple(r.trace_hash for r in first.results) == tuple(
        r.trace_hash for r in second.results
    )

    # 5. Ratify.
    report = ratify(
        course_id=course.course_id,
        source_bundle_sha=course.source_bundle_sha,
        validated_set_sha=course.validated_set_sha,
        course_sha256=course.course_sha256,
        plan_sha256=plan.plan_sha256,
        validated_set=validated,
        first_run=first.results,
        second_run=second.results,
        issued_at="2026-05-16T00:00:00Z",
    )
    assert report.ratified is True, (
        f"micro course failed ratification: {report.failure_reasons}"
    )
    assert verify_report(report) is True

    # 6. Promote.
    index = MasteredCoursesIndex(tmp_path / "mastered.json")
    result = promote(
        report=report, spec=spec, validated_set=validated, index=index,
    )
    assert result.idempotent_skipped is False
    assert len(result.promoted) == len(validated.relations)
    assert all(p.example.accepted for p in result.promoted)
    assert index.contains_course(course.course_id)
    assert index.contains_report(report.report_sha256)

    # 7. Idempotency.
    again = promote(
        report=report, spec=spec, validated_set=validated, index=index,
    )
    assert again.idempotent_skipped is True


def test_micro_course_halts_on_versor_violation() -> None:
    allowlist = SourceAllowlist((
        AllowedSource(_PRIMARY, "primary", "stanford-textbook"),
    ))
    forge = Forge(allowlist=allowlist)
    validated = _build_validated_set(forge)
    spec = SubjectSpec(
        subject_id="subject.micro", title="Micro", target_depth="introductory",
    )
    course = compose(validated_set=validated, spec=spec, source_bundle_sha="0" * 64)
    plan = compile_course(course)

    def angry(step: PlanStep) -> TurnObservation:
        return TurnObservation(
            trace_hash="t", versor_condition=1.0e-3, accepted=True, has_provenance=True,
        )
    out = run_plan(plan, angry)
    assert out.halted is True
    assert out.halt_step_index == 0
