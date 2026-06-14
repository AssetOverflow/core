"""B4 workbench mapping — engine LeewayRecord -> LeewayEvidence.

A pure projection across the read-only firewall: no reliability_gate import,
honest absence preserved, and unexpected enum values clamped to safe defaults.
"""

from __future__ import annotations

from types import SimpleNamespace

from core.cognition.leeway import build_leeway_record
from workbench.api import _leeway_evidence_from_result


def test_absent_record_maps_to_none() -> None:
    # Pre-B4 results carry no leeway -> honest absence (UI shows "not recorded").
    assert _leeway_evidence_from_result(SimpleNamespace(leeway=None)) is None
    assert _leeway_evidence_from_result(SimpleNamespace()) is None


def test_strict_record_maps_field_for_field() -> None:
    rec = build_leeway_record(reach_level="strict", license_decision=None)
    ev = _leeway_evidence_from_result(SimpleNamespace(leeway=rec))
    assert ev is not None
    assert ev.license == "unknown"
    assert ev.claim_disclosure == "none"
    assert ev.class_name == "none"
    assert ev.theta is None


def test_earned_serve_record_maps() -> None:
    ld = SimpleNamespace(
        class_name="addition.converse",
        action=SimpleNamespace(name="SERVE"),
        checker="reliability",
        measured=0.995,
        required=0.99,
        licensed=True,
    )
    rec = build_leeway_record(reach_level="approximate", license_decision=ld)
    ev = _leeway_evidence_from_result(SimpleNamespace(leeway=rec))
    assert ev is not None
    assert ev.license == "SERVE"
    assert ev.theta == 0.99
    assert ev.claim_disclosure == "approximate"
    assert ev.calibration_evidence_ref == "addition.converse"
    assert ev.source_digest is not None


def test_unexpected_enums_clamp_to_safe_defaults() -> None:
    # The workbench faithfully maps any *schema-valid* value (the "never emit
    # verified" guarantee is engine-side); only genuinely invalid enum values
    # are clamped to the safe default.
    bad = SimpleNamespace(
        leeway=SimpleNamespace(
            class_name="x",
            license="WIDE_OPEN",  # not a valid license -> unknown
            theta=0.5,
            claim_disclosure="wild_guess",  # not a valid disclosure -> none
            source_digest=None,
            calibration_evidence_ref=None,
        )
    )
    ev = _leeway_evidence_from_result(bad)
    assert ev is not None
    assert ev.license == "unknown"
    assert ev.claim_disclosure == "none"
