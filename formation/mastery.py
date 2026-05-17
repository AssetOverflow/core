"""``MasteryReport`` self-sealing and emission helpers.

A ``MasteryReport`` is the cryptographic receipt at the end of Stage 7
(Ratify).  It is the only artifact whose SHA authorizes Stage 8 (Promote).

The seal works by computing SHA-256 over the canonical JSON of the report's
dict form with ``report_sha256`` blanked to the empty string, then writing
the SHA into the field.  ``verify_seal`` reproduces the process.  See
``formation/hashing.py`` for the primitive.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from formation.course import GateMeasurement, MasteryReport
from formation.hashing import self_seal, verify_seal


def _iso_utc_now() -> str:
    """Return current time as a stable ISO-8601 UTC string with no microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def report_to_dict(report: MasteryReport) -> dict[str, Any]:
    """Project a ``MasteryReport`` to a canonical-JSON-safe dict."""
    return {
        "schema_version": report.schema_version,
        "course_id": report.course_id,
        "source_bundle_sha": report.source_bundle_sha,
        "validated_set_sha": report.validated_set_sha,
        "course_sha256": report.course_sha256,
        "plan_sha256": report.plan_sha256,
        "gates": [
            {
                "name": g.name,
                "passed": g.passed,
                "measurement": g.measurement,
                "threshold": g.threshold,
            }
            for g in report.gates
        ],
        "trace_hashes": list(report.trace_hashes),
        "ratified": report.ratified,
        "issued_at": report.issued_at,
        "failure_reasons": list(report.failure_reasons),
        "report_sha256": report.report_sha256,
    }


def emit_report(
    *,
    course_id: str,
    source_bundle_sha: str,
    validated_set_sha: str,
    course_sha256: str,
    plan_sha256: str,
    gates: tuple[GateMeasurement, ...],
    trace_hashes: tuple[str, ...],
    failure_reasons: tuple[str, ...] = (),
    issued_at: str | None = None,
) -> MasteryReport:
    """Emit a fully-sealed ``MasteryReport``.

    ``ratified`` is derived: True iff every gate passed.
    """
    ratified = all(g.passed for g in gates) and not failure_reasons
    when = issued_at if issued_at is not None else _iso_utc_now()
    draft = MasteryReport(
        course_id=course_id,
        source_bundle_sha=source_bundle_sha,
        validated_set_sha=validated_set_sha,
        course_sha256=course_sha256,
        plan_sha256=plan_sha256,
        gates=gates,
        trace_hashes=trace_hashes,
        ratified=ratified,
        report_sha256="",
        issued_at=when,
        failure_reasons=failure_reasons,
    )
    sealed = self_seal(report_to_dict(draft), sha_field="report_sha256")
    return MasteryReport(
        course_id=course_id,
        source_bundle_sha=source_bundle_sha,
        validated_set_sha=validated_set_sha,
        course_sha256=course_sha256,
        plan_sha256=plan_sha256,
        gates=gates,
        trace_hashes=trace_hashes,
        ratified=ratified,
        report_sha256=sealed["report_sha256"],
        issued_at=when,
        failure_reasons=failure_reasons,
    )


def verify_report(report: MasteryReport) -> bool:
    """Return True iff ``report.report_sha256`` matches its self-sealing SHA."""
    return verify_seal(report_to_dict(report), sha_field="report_sha256")
