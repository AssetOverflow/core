"""ADR-0106 — expert-demo promotion contract invariants.

Pins three load-bearing invariants:

1. ``expert_demo_requires_signature`` — no domain row may carry
   ``audit_passed=true`` without a corresponding ``expert_demo_claims``
   entry whose digest reproduces the on-disk evidence bundle.

2. ``expert_demo_domain_aware`` — the reporting layer must consult only
   lanes attached to a domain's ratified packs when computing
   ``expert_demo``. Cross-domain lane bleed (e.g. cognition-lane metrics
   deciding a math promotion) is refused.

3. ``expert_demo_replay_byte_equality`` — re-running every consulted
   lane at ``evidence_revision`` must reproduce the exact JSON bytes
   hashed into ``claim_digest``. Drift demotes the row back to
   ``reasoning-capable``.

The current main-branch state of the ledger has zero domains with
``audit_passed=true``; these tests synthesize fixtures to prove the gate
behaves as ADR-0106 specifies, without flipping any production row.
"""

from __future__ import annotations

import json

from core.capability.expert_demo import (
    derive_evidence_digest,
    evaluate_expert_demo,
)
from core.capability.reviewers import (
    ExpertDemoClaim,
    Reviewer,
    ReviewerRegistry,
)


_GOOD_METRICS = {
    "surface_groundedness": 0.97,
    "term_capture_rate": 0.90,
    "intent_accuracy": 0.96,
    "versor_closure_rate": 1.0,
}
_FAB_METRICS = {
    "by_class": {
        "phantom_endpoint": {"n": 3, "refused": 3, "fabricated": 0},
        "cross_pack_non_bridge": {"n": 3, "refused": 3, "fabricated": 0},
        "sibling_collapse": {"n": 3, "refused": 3, "fabricated": 0},
    }
}
_INFERENCE_METRICS = {
    "all_pass_rate": 0.98,
    "replay_determinism": 1.0,
    "overall_pass": True,
}
_ACCURACY_METRICS = {"accuracy": 0.98, "passed": 39, "total": 40}


_SHAPE_FIXTURES = {
    "fabrication_control": _FAB_METRICS,
    "inference_closure": _INFERENCE_METRICS,
    "elementary_mathematics_ood": _ACCURACY_METRICS,
    "foundational_physics_ood": _ACCURACY_METRICS,
    "symbolic_logic": _ACCURACY_METRICS,
    "hebrew_fluency": _ACCURACY_METRICS,
    "koine_greek_fluency": _ACCURACY_METRICS,
}


def _primary_reviewer() -> Reviewer:
    return Reviewer(
        reviewer_id="shay-j",
        display_name="Joshua Shay",
        role="primary",
        domains=("*",),
        review_scope=("pack", "proposal", "chain", "eval"),
        provenance="adr-0092:bootstrap:2026-05-21",
    )


def _build_registry(
    reviewers: tuple[Reviewer, ...],
    claims: tuple[ExpertDemoClaim, ...] = (),
) -> ReviewerRegistry:
    return ReviewerRegistry(
        schema_version=1, reviewers=reviewers, expert_demo_claims=claims
    )


def _good_lane_results(lanes: tuple[str, ...]) -> dict[str, dict[str, dict]]:
    """Build shape-appropriate good metrics per registered lane.

    Lanes not in the shape-fixture map (e.g. synthetic 'a', 'b', 'c'
    used in digest-ordering tests, or 'cognition') get cognition-shape
    metrics as a deterministic default — they're never run through
    the threshold checker in those tests.
    """
    out: dict[str, dict[str, dict]] = {}
    for lane in lanes:
        metrics = _SHAPE_FIXTURES.get(lane, _GOOD_METRICS)
        out[lane] = {
            "public": json.loads(json.dumps(metrics)),
            "holdout": json.loads(json.dumps(metrics)),
        }
    return out


class TestExpertDemoRequiresSignature:
    def test_no_claim_refuses_promotion(self) -> None:
        registry = _build_registry((_primary_reviewer(),))
        verdict = evaluate_expert_demo(
            domain_id="mathematics_logic",
            reasoning_capable=True,
            registry=registry,
            domain_lanes=("inference_closure", "fabrication_control"),
            lane_results=_good_lane_results(
                ("inference_closure", "fabrication_control")
            ),
        )
        assert verdict.passed is False
        assert "no audit_passed_claims entry" in verdict.reason

    def test_unsigned_lanes_refuse_promotion(self) -> None:
        registry = _build_registry(())
        verdict = evaluate_expert_demo(
            domain_id="mathematics_logic",
            reasoning_capable=True,
            registry=registry,
            domain_lanes=("inference_closure",),
            lane_results=_good_lane_results(("inference_closure",)),
        )
        assert verdict.passed is False

    def test_not_reasoning_capable_refuses_promotion(self) -> None:
        registry = _build_registry((_primary_reviewer(),))
        verdict = evaluate_expert_demo(
            domain_id="mathematics_logic",
            reasoning_capable=False,
            registry=registry,
            domain_lanes=("inference_closure",),
            lane_results=_good_lane_results(("inference_closure",)),
        )
        assert verdict.passed is False
        assert "not yet reasoning-capable" in verdict.reason

    def test_signer_without_eval_scope_refuses_promotion(self) -> None:
        domain = "mathematics_logic"
        reviewer = Reviewer(
            reviewer_id="math-pack-reviewer",
            display_name="Math Pack Reviewer",
            role="domain",
            domains=(domain,),
            review_scope=("pack", "chain"),
            provenance="adr-0092:bootstrap:2026-05-21",
        )
        lanes = ("inference_closure", "fabrication_control")
        results = _good_lane_results(lanes)
        digest = derive_evidence_digest(
            domain_id=domain,
            evidence_revision="abc123",
            evidence_lanes=lanes,
            lane_results=results,
        )
        claim = ExpertDemoClaim(
            domain_id=domain,
            evidence_lanes=lanes,
            evidence_revision="abc123",
            signed_by="math-pack-reviewer",
            claim_digest=digest,
        )
        registry = _build_registry((reviewer,), (claim,))
        verdict = evaluate_expert_demo(
            domain_id=domain,
            reasoning_capable=True,
            registry=registry,
            domain_lanes=lanes,
            lane_results=results,
        )
        assert verdict.passed is False
        assert "cannot review eval-scope" in verdict.reason


class TestExpertDemoDomainAware:
    def test_cross_domain_lane_bleed_refused(self) -> None:
        """A claim that cites a cognition lane for a math promotion fails."""
        domain = "mathematics_logic"
        math_lanes = ("inference_closure", "fabrication_control")
        bad_claim_lanes = ("cognition",)
        results = _good_lane_results(bad_claim_lanes + math_lanes)
        digest = derive_evidence_digest(
            domain_id=domain,
            evidence_revision="rev1",
            evidence_lanes=bad_claim_lanes,
            lane_results=results,
        )
        claim = ExpertDemoClaim(
            domain_id=domain,
            evidence_lanes=bad_claim_lanes,
            evidence_revision="rev1",
            signed_by="shay-j",
            claim_digest=digest,
        )
        registry = _build_registry((_primary_reviewer(),), (claim,))
        verdict = evaluate_expert_demo(
            domain_id=domain,
            reasoning_capable=True,
            registry=registry,
            domain_lanes=math_lanes,
            lane_results=results,
        )
        assert verdict.passed is False
        assert "lanes not attached to domain" in verdict.reason

    def test_in_domain_lanes_accepted(self) -> None:
        domain = "mathematics_logic"
        lanes = ("inference_closure", "fabrication_control")
        results = _good_lane_results(lanes)
        digest = derive_evidence_digest(
            domain_id=domain,
            evidence_revision="rev1",
            evidence_lanes=lanes,
            lane_results=results,
        )
        claim = ExpertDemoClaim(
            domain_id=domain,
            evidence_lanes=lanes,
            evidence_revision="rev1",
            signed_by="shay-j",
            claim_digest=digest,
        )
        registry = _build_registry((_primary_reviewer(),), (claim,))
        verdict = evaluate_expert_demo(
            domain_id=domain,
            reasoning_capable=True,
            registry=registry,
            domain_lanes=lanes,
            lane_results=results,
        )
        assert verdict.passed is True
        assert verdict.derived_digest == digest


class TestExpertDemoReplayByteEquality:
    def test_digest_is_stable_across_invocations(self) -> None:
        lanes = ("inference_closure", "fabrication_control")
        results = _good_lane_results(lanes)
        first = derive_evidence_digest(
            domain_id="mathematics_logic",
            evidence_revision="rev1",
            evidence_lanes=lanes,
            lane_results=results,
        )
        second = derive_evidence_digest(
            domain_id="mathematics_logic",
            evidence_revision="rev1",
            evidence_lanes=lanes,
            lane_results=results,
        )
        assert first == second

    def test_digest_is_order_independent_on_lanes(self) -> None:
        results = _good_lane_results(("a", "b", "c"))
        d1 = derive_evidence_digest(
            domain_id="d",
            evidence_revision="rev1",
            evidence_lanes=("a", "b", "c"),
            lane_results=results,
        )
        d2 = derive_evidence_digest(
            domain_id="d",
            evidence_revision="rev1",
            evidence_lanes=("c", "a", "b"),
            lane_results=results,
        )
        assert d1 == d2

    def test_drift_in_results_demotes_row(self) -> None:
        domain = "mathematics_logic"
        lanes = ("inference_closure", "fabrication_control")
        original = _good_lane_results(lanes)
        original_digest = derive_evidence_digest(
            domain_id=domain,
            evidence_revision="rev1",
            evidence_lanes=lanes,
            lane_results=original,
        )
        claim = ExpertDemoClaim(
            domain_id=domain,
            evidence_lanes=lanes,
            evidence_revision="rev1",
            signed_by="shay-j",
            claim_digest=original_digest,
        )
        drifted = _good_lane_results(lanes)
        drifted["inference_closure"]["public"]["all_pass_rate"] = 0.97
        registry = _build_registry((_primary_reviewer(),), (claim,))
        verdict = evaluate_expert_demo(
            domain_id=domain,
            reasoning_capable=True,
            registry=registry,
            domain_lanes=lanes,
            lane_results=drifted,
        )
        assert verdict.passed is False
        assert "replay drift" in verdict.reason
        assert verdict.derived_digest is not None
        assert verdict.derived_digest != original_digest


class TestExpertDemoThresholds:
    def test_below_threshold_metric_refuses(self) -> None:
        domain = "mathematics_logic"
        lanes = ("inference_closure", "fabrication_control")
        results = _good_lane_results(lanes)
        results["inference_closure"]["holdout"]["all_pass_rate"] = 0.50
        digest = derive_evidence_digest(
            domain_id=domain,
            evidence_revision="rev1",
            evidence_lanes=lanes,
            lane_results=results,
        )
        claim = ExpertDemoClaim(
            domain_id=domain,
            evidence_lanes=lanes,
            evidence_revision="rev1",
            signed_by="shay-j",
            claim_digest=digest,
        )
        registry = _build_registry((_primary_reviewer(),), (claim,))
        verdict = evaluate_expert_demo(
            domain_id=domain,
            reasoning_capable=True,
            registry=registry,
            domain_lanes=lanes,
            lane_results=results,
        )
        assert verdict.passed is False
        assert "all_pass_rate" in verdict.reason
        assert "below threshold" in verdict.reason

    def test_fabrication_control_failure_refuses(self) -> None:
        domain = "mathematics_logic"
        lanes = ("inference_closure", "fabrication_control")
        results = _good_lane_results(lanes)
        results["fabrication_control"]["holdout"]["by_class"][
            "phantom_endpoint"
        ]["fabricated"] = 1
        digest = derive_evidence_digest(
            domain_id=domain,
            evidence_revision="rev1",
            evidence_lanes=lanes,
            lane_results=results,
        )
        claim = ExpertDemoClaim(
            domain_id=domain,
            evidence_lanes=lanes,
            evidence_revision="rev1",
            signed_by="shay-j",
            claim_digest=digest,
        )
        registry = _build_registry((_primary_reviewer(),), (claim,))
        verdict = evaluate_expert_demo(
            domain_id=domain,
            reasoning_capable=True,
            registry=registry,
            domain_lanes=lanes,
            lane_results=results,
        )
        assert verdict.passed is False
        assert "fabrication_control" in verdict.reason


class TestProductionLedgerPromotionsAreSignedOnly:
    """ADR-0106 §Acceptance preserved post-ADR-0110.

    Originally tested that NO domain row carried ``audit_passed=true``
    because no signed claims existed yet. After ADR-0110, the math
    domain carries a signed claim. The load-bearing invariant remains:
    every promoted domain must trace back to a signed claim in the
    reviewer registry. A silent code-only promotion would be caught here.
    """

    def test_every_promoted_domain_has_signed_claim(self) -> None:
        from pathlib import Path

        from core.capability.reporting import ledger_report
        from core.capability.reviewers import load_reviewer_registry
        from core.capability.sources import LEDGER_SOURCES

        repo_root = Path(__file__).resolve().parent.parent
        registry = load_reviewer_registry(repo_root / LEDGER_SOURCES.reviewers)
        report = ledger_report()
        for row in report.get("domains", []):
            if not row.get("predicates", {}).get("expert_demo"):
                continue
            domain = row["domain"]
            claim = registry.expert_demo_claim_for(domain)
            assert claim is not None, (
                f"domain {domain!r} reports audit_passed=true but has no "
                f"signed expert_demo_claims entry"
            )
