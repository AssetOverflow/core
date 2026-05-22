"""ADR-0124 — `systems_software` audit-passed promotion invariants.

Pins four load-bearing invariants:

1. ``row_is_audit_passed`` — ``ledger_report()`` reports
   ``systems_software`` at ``status="audit-passed"`` with
   ``predicates.audit_passed == True``.

2. ``replay_digest_byte_equality`` — re-deriving the
   evidence-bundle digest from the on-disk lane result files reproduces
   the signed ``claim_digest`` byte-for-byte (ADR-0106 §1.5).

3. ``other_domains_unaffected`` — ADR-0124 promotes exactly
   one new domain. ``mathematics_logic`` and ``physics`` must remain
   promoted; ``hebrew_greek_textual_reasoning`` and
   ``philosophy_theology`` must remain at ``audit_passed=false``.

4. ``distinct_digest_from_adr_0110_and_0111`` — systems_software digest,
   physics digest, and math digest must differ, demonstrating the bundle's
   ``domain_id`` + ``evidence_revision`` fields produce distinct
   claims even when two of three evidence lanes are shared.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.capability.expert_demo import (
    derive_evidence_digest,
    materialise_lane_results,
)
from core.capability.reporting import _latest_eval_result, ledger_report
from core.capability.reviewers import load_reviewer_registry
from core.capability.sources import LEDGER_SOURCES


_REPO_ROOT = Path(__file__).resolve().parent.parent

_SYSTEMS_SOFTWARE_LANES = (
    "symbolic_logic",
    "inference_closure",
    "fabrication_control",
)


def _fetch(lane: str, split: str) -> dict[str, Any]:
    payload = _latest_eval_result(lane, "v1", split)
    metrics = dict(payload.get("metrics", {}) or {})
    if "by_class" not in metrics and "by_class" in payload:
        metrics["by_class"] = payload["by_class"]
    return metrics


def _systems_software_row() -> dict:
    report = ledger_report()
    for row in report["domains"]:
        if row["domain"] == "systems_software":
            return row
    raise AssertionError("systems_software row missing from ledger_report()")


def _registry():
    registry_path = _REPO_ROOT / LEDGER_SOURCES.reviewers
    return load_reviewer_registry(registry_path)


def _systems_software_claim():
    claim = _registry().expert_demo_claim_for("systems_software")
    assert claim is not None, "expert_demo_claims entry for systems_software missing"
    return claim


class TestAdr0124SystemsSoftwareAuditPassedHolds:
    def test_systems_software_row_is_audit_passed(self) -> None:
        row = _systems_software_row()
        assert row["status"] == "audit-passed"
        assert row["predicates"]["audit_passed"] is True

    def test_signed_claim_is_present(self) -> None:
        claim = _systems_software_claim()
        assert set(claim.evidence_lanes) == set(_SYSTEMS_SOFTWARE_LANES)
        assert claim.signed_by == "shay-j"
        assert claim.evidence_revision == "adr-0124:reviewed:2026-05-22"


class TestAdr0124ReplayDigestByteEquality:
    def test_derived_digest_matches_signed_claim(self) -> None:
        claim = _systems_software_claim()
        lane_results = materialise_lane_results(
            _SYSTEMS_SOFTWARE_LANES, fetch_split=_fetch
        )
        derived = derive_evidence_digest(
            domain_id="systems_software",
            evidence_revision=claim.evidence_revision,
            evidence_lanes=claim.evidence_lanes,
            lane_results=lane_results,
        )
        assert derived == claim.claim_digest


class TestAdr0124OtherDomainsUnaffected:
    def test_math_and_physics_remain_promoted(self) -> None:
        promoted = {
            row["domain"]
            for row in ledger_report()["domains"]
            if row["predicates"]["audit_passed"]
        }
        assert "mathematics_logic" in promoted
        assert "physics" in promoted
        assert "systems_software" in promoted

    def test_unpromoted_domains_stay_reasoning_capable(self) -> None:
        unpromoted_expected = {
            "hebrew_greek_textual_reasoning",
            "philosophy_theology",
        }
        report = ledger_report()
        for row in report["domains"]:
            if row["domain"] in unpromoted_expected:
                assert row["status"] == "reasoning-capable", (
                    f"{row['domain']} expected reasoning-capable, "
                    f"got {row['status']}"
                )
                assert row["predicates"]["audit_passed"] is False


class TestAdr0124DistinctDigestFromAdr0110And0111:
    def test_systems_software_digest_differs_from_others(self) -> None:
        registry = _registry()
        systems_software_claim = registry.expert_demo_claim_for("systems_software")
        physics_claim = registry.expert_demo_claim_for("physics")
        math_claim = registry.expert_demo_claim_for("mathematics_logic")
        assert systems_software_claim is not None
        assert physics_claim is not None
        assert math_claim is not None
        assert systems_software_claim.claim_digest != physics_claim.claim_digest
        assert systems_software_claim.claim_digest != math_claim.claim_digest

    def test_two_of_three_lanes_are_shared(self) -> None:
        """Same shared lanes, distinct digests — proves domain_id matters."""
        registry = _registry()
        systems_software_claim = registry.expert_demo_claim_for("systems_software")
        physics_claim = registry.expert_demo_claim_for("physics")
        math_claim = registry.expert_demo_claim_for("mathematics_logic")
        assert systems_software_claim is not None
        assert physics_claim is not None
        assert math_claim is not None
        
        shared_physics = set(systems_software_claim.evidence_lanes) & set(physics_claim.evidence_lanes)
        assert shared_physics == {"inference_closure", "fabrication_control"}

        shared_math = set(systems_software_claim.evidence_lanes) & set(math_claim.evidence_lanes)
        assert shared_math == {"inference_closure", "fabrication_control"}
