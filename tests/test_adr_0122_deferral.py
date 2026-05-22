"""ADR-0122 — systems_software audit-passed promotion deferred.

Pins the deferral invariants:

1. systems_software stays reasoning-capable with audit_passed=false.
2. The blocker is the named symbolic_logic shape mismatch.
"""

from __future__ import annotations

from core.capability.expert_demo import evaluate_expert_demo, materialise_lane_results
from core.capability.reporting import _latest_eval_result, ledger_report
from core.capability.reviewers import ExpertDemoClaim, Reviewer, ReviewerRegistry


_SYSTEMS_LANES = ("symbolic_logic", "inference_closure", "fabrication_control")


def _fetch(lane: str, split: str) -> dict[str, object]:
    payload = _latest_eval_result(lane, "v1", split)
    metrics = dict(payload.get("metrics", {}) or {})
    if "by_class" not in metrics and "by_class" in payload:
        metrics["by_class"] = payload["by_class"]
    return metrics


def _systems_row() -> dict:
    rows = {row["domain"]: row for row in ledger_report()["domains"]}
    return rows["systems_software"]


class TestAdr0122Deferral:
    def test_systems_software_stays_reasoning_capable(self) -> None:
        row = _systems_row()
        assert row["status"] == "reasoning-capable"
        assert row["predicates"]["reasoning_capable"] is True
        assert row["predicates"]["audit_passed"] is False

    def test_named_blocker_matches_gate_reason(self) -> None:
        from pathlib import Path
        from core.capability.reviewers import load_reviewer_registry
        from core.capability.sources import LEDGER_SOURCES

        repo_root = Path(__file__).resolve().parent.parent
        registry = load_reviewer_registry(repo_root / LEDGER_SOURCES.reviewers)
        lane_results = materialise_lane_results(_SYSTEMS_LANES, fetch_split=_fetch)

        verdict = evaluate_expert_demo(
            domain_id="systems_software",
            reasoning_capable=True,
            registry=registry,
            domain_lanes=_SYSTEMS_LANES,
            lane_results=lane_results,
        )

        assert verdict.passed is False
        assert verdict.reason == "no audit_passed_claims entry for this domain"
