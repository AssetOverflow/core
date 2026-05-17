"""Tests for ``formation.ratify`` — Stage 7 gate checks."""

from __future__ import annotations

import pytest

from formation.candidate import RelationCandidate, SourceRef
from formation.course import ValidatedTripleSet
from formation.mastery import verify_report
from formation.ratify import StepResult, ratify


def _src() -> SourceRef:
    return SourceRef(
        source_sha="a" * 64,
        span="span",
        adapter="wikipedia",
        retrieved_at="2026-05-16T00:00:00Z",
    )


def _r(head: str, relation: str, tail: str) -> RelationCandidate:
    return RelationCandidate(head=head, relation=relation, tail=tail, sources=(_src(),))


def _vts(*triples: tuple[str, str, str]) -> ValidatedTripleSet:
    return ValidatedTripleSet(
        subject_id="subject.x",
        concepts=(),
        relations=tuple(_r(h, r, t) for h, r, t in triples),
        counters=(),
        ordering_hints=(),
    )


def _step(
    step_type: str,
    head: str = "",
    relation: str = "",
    tail: str = "",
    trace: str = "t",
    accepted: bool = True,
    has_provenance: bool = True,
    vc: str = "0.0",
) -> StepResult:
    payload: dict[str, object] = {}
    if head:
        payload["head"] = head
    if relation:
        payload["relation"] = relation
    if tail:
        payload["tail"] = tail
    return StepResult(
        step_type=step_type,
        payload=payload,
        trace_hash=trace,
        versor_condition_repr=vc,
        accepted=accepted,
        has_provenance=has_provenance,
    )


_BASE_KW = dict(
    course_id="x.v1",
    source_bundle_sha="0" * 64,
    validated_set_sha="1" * 64,
    course_sha256="2" * 64,
    plan_sha256="3" * 64,
    issued_at="2026-05-16T00:00:00Z",
)


class TestAllGatesGreen:
    def test_full_ratification(self) -> None:
        vts = _vts(("wisdom", "is", "judgment"))
        run = (
            _step("seed_concept", trace="t1"),
            _step("introduce_relation", "wisdom", "is", "judgment", trace="t2"),
            _step("walk_step", "wisdom", "is", "judgment", trace="t3"),
            _step("adversarial_probe", trace="t4", accepted=False),
            _step("replay_assertion", trace="t5"),
        )
        rpt = ratify(
            validated_set=vts,
            first_run=run,
            second_run=run,
            **_BASE_KW,
        )
        assert rpt.ratified is True
        assert verify_report(rpt) is True
        assert all(g.passed for g in rpt.gates)
        assert rpt.failure_reasons == ()


class TestG1Replay:
    def test_trace_mismatch_fails(self) -> None:
        vts = _vts(("a", "is", "b"))
        first = (_step("walk_step", "a", "is", "b", trace="t1"),)
        second = (_step("walk_step", "a", "is", "b", trace="DIFFERENT"),)
        rpt = ratify(validated_set=vts, first_run=first, second_run=second, **_BASE_KW)
        g1 = next(g for g in rpt.gates if g.name == "G1_replay_determinism")
        assert g1.passed is False
        assert rpt.ratified is False

    def test_length_mismatch_fails(self) -> None:
        vts = _vts(("a", "is", "b"))
        first = (_step("walk_step", "a", "is", "b", trace="t1"),)
        second: tuple[StepResult, ...] = ()
        rpt = ratify(validated_set=vts, first_run=first, second_run=second, **_BASE_KW)
        assert rpt.ratified is False


class TestG3Adversarial:
    def test_adversarial_accepted_fails(self) -> None:
        vts = _vts(("a", "is", "b"))
        run = (
            _step("walk_step", "a", "is", "b", trace="t1"),
            _step("adversarial_probe", trace="t2", accepted=True),
        )
        rpt = ratify(validated_set=vts, first_run=run, second_run=run, **_BASE_KW)
        g3 = next(g for g in rpt.gates if g.name == "G3_adversarial_rejection_rate")
        assert g3.passed is False


class TestG4Legit:
    def test_legit_rejection_fails(self) -> None:
        vts = _vts(("a", "is", "b"))
        run = (_step("walk_step", "a", "is", "b", trace="t1", accepted=False),)
        rpt = ratify(validated_set=vts, first_run=run, second_run=run, **_BASE_KW)
        g4 = next(g for g in rpt.gates if g.name == "G4_legitimate_acceptance_rate")
        assert g4.passed is False


class TestG5Provenance:
    def test_missing_provenance_fails(self) -> None:
        vts = _vts(("a", "is", "b"))
        run = (_step("walk_step", "a", "is", "b", trace="t1", has_provenance=False),)
        rpt = ratify(validated_set=vts, first_run=run, second_run=run, **_BASE_KW)
        g5 = next(g for g in rpt.gates if g.name == "G5_provenance_nonempty_rate")
        assert g5.passed is False


class TestG6Coverage:
    def test_unwalked_relation_fails(self) -> None:
        vts = _vts(("wisdom", "is", "judgment"), ("number", "is", "quantity"))
        run = (
            _step("walk_step", "wisdom", "is", "judgment", trace="t1"),
            # "number is quantity" never walked.
        )
        rpt = ratify(validated_set=vts, first_run=run, second_run=run, **_BASE_KW)
        g6 = next(g for g in rpt.gates if g.name == "G6_phase2_relation_coverage")
        assert g6.passed is False
        assert any("unwalked_relations" in r for r in rpt.failure_reasons)

    def test_all_walked_passes(self) -> None:
        vts = _vts(("wisdom", "is", "judgment"), ("number", "is", "quantity"))
        run = (
            _step("walk_step", "wisdom", "is", "judgment", trace="t1"),
            _step("walk_step", "number", "is", "quantity", trace="t2"),
        )
        rpt = ratify(validated_set=vts, first_run=run, second_run=run, **_BASE_KW)
        g6 = next(g for g in rpt.gates if g.name == "G6_phase2_relation_coverage")
        assert g6.passed is True


class TestEmptyInputs:
    def test_no_steps_ratifies_when_no_required_relations(self) -> None:
        vts = _vts()  # no relations required
        rpt = ratify(validated_set=vts, first_run=(), second_run=(), **_BASE_KW)
        # All gate ratios are "n/a" → considered passed.
        assert all(g.passed for g in rpt.gates)
        assert rpt.ratified is True
