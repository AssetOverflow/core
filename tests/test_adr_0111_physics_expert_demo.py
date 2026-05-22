"""ADR-0111 — `physics` expert-demo promotion invariants.

Pins four load-bearing invariants:

1. ``adr_0111_physics_expert_demo_holds`` — ``ledger_report()`` reports
   ``physics`` at ``status="audit-passed"`` with
   ``predicates.audit_passed == True``.

2. ``adr_0111_replay_digest_byte_equality`` — re-deriving the
   evidence-bundle digest from the on-disk lane result files reproduces
   the signed ``claim_digest`` byte-for-byte (ADR-0106 §1.5).

3. ``adr_0111_other_domains_unaffected`` — ADR-0111 promotes exactly
   one new domain. ``mathematics_logic`` (ADR-0110) must remain
   promoted; ``systems_software``, ``hebrew_greek_textual_reasoning``,
   and ``philosophy_theology`` must remain at ``audit_passed=false``.

4. ``adr_0111_distinct_digest_from_adr_0110`` — physics digest and
   math digest must differ, demonstrating the bundle's
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

_PHYSICS_LANES = (
    "foundational_physics_ood",
    "inference_closure",
    "fabrication_control",
)


def _fetch(lane: str, split: str) -> dict[str, Any]:
    payload = _latest_eval_result(lane, "v1", split)
    metrics = dict(payload.get("metrics", {}) or {})
    if "by_class" not in metrics and "by_class" in payload:
        metrics["by_class"] = payload["by_class"]
    return metrics


def _physics_row() -> dict:
    report = ledger_report()
    for row in report["domains"]:
        if row["domain"] == "physics":
            return row
    raise AssertionError("physics row missing from ledger_report()")


def _registry():
    registry_path = _REPO_ROOT / LEDGER_SOURCES.reviewers
    return load_reviewer_registry(registry_path)


def _physics_claim():
    claim = _registry().expert_demo_claim_for("physics")
    assert claim is not None, "expert_demo_claims entry for physics missing"
    return claim


class TestAdr0111PhysicsExpertDemoHolds:
    def test_physics_row_is_expert_demo(self) -> None:
        row = _physics_row()
        assert row["status"] == "audit-passed"
        assert row["predicates"]["audit_passed"] is True

    def test_signed_claim_is_present(self) -> None:
        claim = _physics_claim()
        assert set(claim.evidence_lanes) == set(_PHYSICS_LANES)
        assert claim.signed_by == "shay-j"
        assert claim.evidence_revision == "adr-0111:reviewed:2026-05-22"


class TestAdr0111ReplayDigestByteEquality:
    def test_derived_digest_matches_signed_claim(self) -> None:
        claim = _physics_claim()
        lane_results = materialise_lane_results(
            _PHYSICS_LANES, fetch_split=_fetch
        )
        derived = derive_evidence_digest(
            domain_id="physics",
            evidence_revision=claim.evidence_revision,
            evidence_lanes=claim.evidence_lanes,
            lane_results=lane_results,
        )
        assert derived == claim.claim_digest


class TestAdr0111OtherDomainsUnaffected:
    def test_math_remains_promoted(self) -> None:
        promoted = {
            row["domain"]
            for row in ledger_report()["domains"]
            if row["predicates"]["audit_passed"]
        }
        assert "mathematics_logic" in promoted
        assert "physics" in promoted

    def test_unpromoted_domains_stay_reasoning_capable(self) -> None:
        unpromoted_expected = {
            "systems_software",
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


class TestAdr0111DistinctDigestFromAdr0110:
    def test_physics_digest_differs_from_math_digest(self) -> None:
        registry = _registry()
        physics_claim = registry.expert_demo_claim_for("physics")
        math_claim = registry.expert_demo_claim_for("mathematics_logic")
        assert physics_claim is not None
        assert math_claim is not None
        assert physics_claim.claim_digest != math_claim.claim_digest

    def test_two_of_three_lanes_are_shared(self) -> None:
        """Same shared lanes, distinct digests — proves domain_id matters."""
        registry = _registry()
        physics_claim = registry.expert_demo_claim_for("physics")
        math_claim = registry.expert_demo_claim_for("mathematics_logic")
        assert physics_claim is not None and math_claim is not None
        shared = set(physics_claim.evidence_lanes) & set(math_claim.evidence_lanes)
        assert shared == {"inference_closure", "fabrication_control"}
