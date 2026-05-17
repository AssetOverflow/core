"""Tests for ``formation.index`` and ``formation.promote`` — Stage 8."""

from __future__ import annotations

import pytest

from formation.candidate import CandidateState, RelationCandidate, SourceRef
from formation.course import (
    GateMeasurement,
    MasteryReport,
    SubjectSpec,
    ValidatedTripleSet,
)
from formation.index import MasteredCourseEntry, MasteredCoursesIndex
from formation.mastery import emit_report
from formation.promote import PromoteRefused, promote


def _src() -> SourceRef:
    return SourceRef(
        source_sha="a" * 64,
        span="span",
        adapter="wikipedia",
        retrieved_at="2026-05-16T00:00:00Z",
    )


def _vts(*triples: tuple[str, str, str]) -> ValidatedTripleSet:
    rels = tuple(
        RelationCandidate(
            head=h, relation=r, tail=t, sources=(_src(),),
            state=CandidateState.VALIDATED,
        )
        for h, r, t in triples
    )
    return ValidatedTripleSet(
        subject_id="subject.x",
        concepts=(),
        relations=rels,
        counters=(),
        ordering_hints=(),
    )


def _spec(*requires: str) -> SubjectSpec:
    return SubjectSpec(
        subject_id="subject.x",
        title="Subject X",
        target_depth="introductory",
        requires_courses=requires,
    )


def _report(course_id: str = "x.v1", ratified: bool = True) -> MasteryReport:
    return emit_report(
        course_id=course_id,
        source_bundle_sha="0" * 64,
        validated_set_sha="1" * 64,
        course_sha256="2" * 64,
        plan_sha256="3" * 64,
        gates=(
            GateMeasurement(
                name="g", passed=ratified, measurement="1.0", threshold="1.0",
            ),
        ),
        trace_hashes=("t1",),
        failure_reasons=() if ratified else ("nope",),
        issued_at="2026-05-16T00:00:00Z",
    )


class TestIndex:
    def test_empty_index_round_trips(self, tmp_path) -> None:
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        assert idx.all_courses() == ()
        assert idx.contains_course("x.v1") is False

    def test_add_and_persist(self, tmp_path) -> None:
        path = tmp_path / "idx.json"
        idx = MasteredCoursesIndex(path)
        entry = MasteredCourseEntry(
            course_id="x.v1",
            report_sha256="r" * 64,
            issued_at="2026-05-16T00:00:00Z",
            course_sha256="c" * 64,
            validated_set_sha="v" * 64,
        )
        idx.add(entry)
        # Reload.
        idx2 = MasteredCoursesIndex(path)
        assert idx2.contains_course("x.v1") is True
        assert idx2.contains_report("r" * 64) is True

    def test_add_same_entry_idempotent(self, tmp_path) -> None:
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        entry = MasteredCourseEntry(
            course_id="x.v1", report_sha256="r" * 64,
            issued_at="2026-05-16T00:00:00Z",
            course_sha256="c" * 64, validated_set_sha="v" * 64,
        )
        idx.add(entry)
        idx.add(entry)  # no-op
        assert len(idx.all_courses()) == 1

    def test_conflicting_report_for_same_course_raises(self, tmp_path) -> None:
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        idx.add(MasteredCourseEntry(
            course_id="x.v1", report_sha256="r" * 64,
            issued_at="2026-05-16T00:00:00Z",
            course_sha256="c" * 64, validated_set_sha="v" * 64,
        ))
        with pytest.raises(ValueError, match="different report"):
            idx.add(MasteredCourseEntry(
                course_id="x.v1", report_sha256="r2" * 32,
                issued_at="2026-05-16T00:00:00Z",
                course_sha256="c" * 64, validated_set_sha="v" * 64,
            ))


class TestPromoteGates:
    def test_unratified_report_refused(self, tmp_path) -> None:
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        with pytest.raises(PromoteRefused, match="not ratified"):
            promote(
                report=_report(ratified=False),
                spec=_spec(),
                validated_set=_vts(("wisdom", "is", "judgment")),
                index=idx,
            )

    def test_tampered_seal_refused(self, tmp_path) -> None:
        rpt = _report()
        tampered = MasteryReport(
            course_id="WRONG",  # mutated post-seal
            source_bundle_sha=rpt.source_bundle_sha,
            validated_set_sha=rpt.validated_set_sha,
            course_sha256=rpt.course_sha256,
            plan_sha256=rpt.plan_sha256,
            gates=rpt.gates,
            trace_hashes=rpt.trace_hashes,
            ratified=rpt.ratified,
            report_sha256=rpt.report_sha256,
            issued_at=rpt.issued_at,
            failure_reasons=rpt.failure_reasons,
        )
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        with pytest.raises(PromoteRefused, match="self-seal"):
            promote(
                report=tampered,
                spec=_spec(),
                validated_set=_vts(("wisdom", "is", "judgment")),
                index=idx,
            )

    def test_missing_prerequisite_refused(self, tmp_path) -> None:
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        with pytest.raises(PromoteRefused, match="missing prerequisites"):
            promote(
                report=_report(),
                spec=_spec("not.present.v1"),
                validated_set=_vts(("wisdom", "is", "judgment")),
                index=idx,
            )


class TestPromoteHappyPath:
    def test_promotion_routes_triples_through_review(self, tmp_path) -> None:
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        rpt = _report()
        result = promote(
            report=rpt,
            spec=_spec(),
            validated_set=_vts(("wisdom", "is", "judgment")),
            index=idx,
        )
        assert result.idempotent_skipped is False
        assert len(result.promoted) == 1
        assert result.promoted[0].triple == ("wisdom", "is", "judgment")
        assert result.promoted[0].example.accepted is True
        # Index now has it.
        assert idx.contains_course("x.v1")
        assert idx.contains_report(rpt.report_sha256)

    def test_promotion_idempotent_on_second_call(self, tmp_path) -> None:
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        rpt = _report()
        promote(
            report=rpt, spec=_spec(),
            validated_set=_vts(("wisdom", "is", "judgment")), index=idx,
        )
        result2 = promote(
            report=rpt, spec=_spec(),
            validated_set=_vts(("wisdom", "is", "judgment")), index=idx,
        )
        assert result2.idempotent_skipped is True
        assert result2.promoted == ()


class TestPromoteWithPrerequisites:
    def test_prereq_present_proceeds(self, tmp_path) -> None:
        idx = MasteredCoursesIndex(tmp_path / "idx.json")
        idx.add(MasteredCourseEntry(
            course_id="prereq.v1", report_sha256="p" * 64,
            issued_at="2026-05-16T00:00:00Z",
            course_sha256="c" * 64, validated_set_sha="v" * 64,
        ))
        result = promote(
            report=_report(),
            spec=_spec("prereq.v1"),
            validated_set=_vts(("wisdom", "is", "judgment")),
            index=idx,
        )
        assert result.idempotent_skipped is False
