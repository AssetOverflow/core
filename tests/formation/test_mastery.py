"""Tests for ``formation.mastery`` — self-sealed ``MasteryReport``."""

from __future__ import annotations

import pytest

from formation.course import GateMeasurement, MasteryReport
from formation.mastery import emit_report, report_to_dict, verify_report


def _gate(name: str, passed: bool = True) -> GateMeasurement:
    return GateMeasurement(name=name, passed=passed, measurement="1.0", threshold="1.0")


class TestEmit:
    def test_emits_sealed_report(self) -> None:
        rpt = emit_report(
            course_id="x.v1",
            source_bundle_sha="a" * 64,
            validated_set_sha="b" * 64,
            course_sha256="c" * 64,
            plan_sha256="d" * 64,
            gates=(_gate("g1"),),
            trace_hashes=("h1", "h2"),
            issued_at="2026-05-16T00:00:00Z",
        )
        assert rpt.report_sha256 != ""
        assert verify_report(rpt) is True
        assert rpt.ratified is True

    def test_failure_reasons_set_ratified_false(self) -> None:
        rpt = emit_report(
            course_id="x.v1",
            source_bundle_sha="a" * 64,
            validated_set_sha="b" * 64,
            course_sha256="c" * 64,
            plan_sha256="d" * 64,
            gates=(_gate("g1"),),
            trace_hashes=(),
            failure_reasons=("nope",),
            issued_at="2026-05-16T00:00:00Z",
        )
        assert rpt.ratified is False
        assert verify_report(rpt) is True

    def test_failing_gate_sets_ratified_false(self) -> None:
        rpt = emit_report(
            course_id="x.v1",
            source_bundle_sha="a" * 64,
            validated_set_sha="b" * 64,
            course_sha256="c" * 64,
            plan_sha256="d" * 64,
            gates=(_gate("g1", passed=False),),
            trace_hashes=(),
            issued_at="2026-05-16T00:00:00Z",
        )
        assert rpt.ratified is False


class TestSeal:
    def test_tamper_breaks_verify(self) -> None:
        rpt = emit_report(
            course_id="x.v1",
            source_bundle_sha="a" * 64,
            validated_set_sha="b" * 64,
            course_sha256="c" * 64,
            plan_sha256="d" * 64,
            gates=(_gate("g1"),),
            trace_hashes=("h1",),
            issued_at="2026-05-16T00:00:00Z",
        )
        tampered = MasteryReport(
            course_id="x.v2",  # changed
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
        assert verify_report(tampered) is False

    def test_blank_seal_fails_verify(self) -> None:
        bare = MasteryReport(
            course_id="x.v1",
            source_bundle_sha="a" * 64,
            validated_set_sha="b" * 64,
            course_sha256="c" * 64,
            plan_sha256="d" * 64,
            gates=(),
            trace_hashes=(),
            ratified=True,
        )
        assert verify_report(bare) is False

    def test_seal_is_deterministic(self) -> None:
        # Two emissions with identical inputs (including issued_at) → same SHA.
        kw = dict(
            course_id="x.v1",
            source_bundle_sha="a" * 64,
            validated_set_sha="b" * 64,
            course_sha256="c" * 64,
            plan_sha256="d" * 64,
            gates=(_gate("g1"),),
            trace_hashes=("h1",),
            issued_at="2026-05-16T00:00:00Z",
        )
        a = emit_report(**kw)
        b = emit_report(**kw)
        assert a.report_sha256 == b.report_sha256


class TestProjection:
    def test_report_to_dict_has_no_floats(self) -> None:
        rpt = emit_report(
            course_id="x.v1",
            source_bundle_sha="a" * 64,
            validated_set_sha="b" * 64,
            course_sha256="c" * 64,
            plan_sha256="d" * 64,
            gates=(_gate("g1"),),
            trace_hashes=("h1",),
            issued_at="2026-05-16T00:00:00Z",
        )
        d = report_to_dict(rpt)
        # Walk the dict and assert no floats.
        def walk(x):
            if isinstance(x, float):
                raise AssertionError("float in report dict")
            if isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(d)
