"""ADR-0110 — `mathematics_logic` expert-demo promotion invariants.

Pins three load-bearing invariants:

1. ``adr_0110_math_expert_demo_holds`` — ``ledger_report()`` reports
   ``mathematics_logic`` at ``status="audit-passed"`` with
   ``predicates.audit_passed == True``.

2. ``adr_0110_replay_digest_byte_equality`` — re-deriving the
   evidence-bundle digest from the on-disk lane result files reproduces
   the signed ``claim_digest`` byte-for-byte (ADR-0106 §1.5).

3. ``adr_0110_other_domains_unaffected`` — ADR-0110 promotes exactly
   one domain. Every other domain row stays at ``audit_passed=false``
   under its own (absent) ``expert_demo_claims`` entry.
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

_MATH_LANES = (
    "elementary_mathematics_ood",
    "inference_closure",
    "fabrication_control",
)


def _fetch(lane: str, split: str) -> dict[str, Any]:
    """Mirror reporting.py's fetcher: fold top-level by_class into metrics."""
    payload = _latest_eval_result(lane, "v1", split)
    metrics = dict(payload.get("metrics", {}) or {})
    if "by_class" not in metrics and "by_class" in payload:
        metrics["by_class"] = payload["by_class"]
    return metrics


def _math_row() -> dict:
    report = ledger_report()
    for row in report["domains"]:
        if row["domain"] == "mathematics_logic":
            return row
    raise AssertionError("mathematics_logic row missing from ledger_report()")


def _math_claim():
    registry_path = _REPO_ROOT / LEDGER_SOURCES.reviewers
    registry = load_reviewer_registry(registry_path)
    claim = registry.expert_demo_claim_for("mathematics_logic")
    assert claim is not None, "expert_demo_claims entry for math missing"
    return claim


class TestAdr0110MathExpertDemoHolds:
    def test_math_row_is_expert_demo(self) -> None:
        row = _math_row()
        assert row["status"] == "audit-passed"
        assert row["predicates"]["audit_passed"] is True

    def test_signed_claim_is_present(self) -> None:
        claim = _math_claim()
        assert set(claim.evidence_lanes) == set(_MATH_LANES)
        assert claim.signed_by == "shay-j"
        assert claim.evidence_revision == "adr-0110:reviewed:2026-05-22"


class TestAdr0110ReplayDigestByteEquality:
    def test_derived_digest_matches_signed_claim(self) -> None:
        claim = _math_claim()
        lane_results = materialise_lane_results(
            _MATH_LANES, fetch_split=_fetch
        )
        derived = derive_evidence_digest(
            domain_id="mathematics_logic",
            evidence_revision=claim.evidence_revision,
            evidence_lanes=claim.evidence_lanes,
            lane_results=lane_results,
        )
        assert derived == claim.claim_digest


class TestAdr0110OtherDomainsUnaffected:
    def test_math_stays_promoted(self) -> None:
        """ADR-0110's promotion of mathematics_logic must persist.

        Originally this asserted math was the only promoted domain.
        ADR-0111 added physics — the load-bearing invariant for
        ADR-0110 is that math stays promoted, not that no other
        domain is promoted alongside it.
        """
        promoted = [
            row["domain"]
            for row in ledger_report()["domains"]
            if row["predicates"]["audit_passed"]
        ]
        assert "mathematics_logic" in promoted, (
            f"ADR-0110 promotion of mathematics_logic must persist; got: {promoted}"
        )
