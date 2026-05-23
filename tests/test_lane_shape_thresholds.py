"""ADR-0109 — lane-shape-aware threshold invariants.

Pins four invariants:

1. ``lane_shape_explicit`` — every lane id referenced by any ratified
   pack's manifest must resolve to a registered shape.
2. ``shape_thresholds_are_named`` — each registered shape has a
   documented checker; no implicit defaults.
3. ``unknown_lane_fails_closed`` — a lane id absent from the registry
   produces ``passed=False`` with a named reason.
4. ``cognition_shape_unchanged_under_amendment`` — the four cognition
   threshold constants are bit-identical to ADR-0106 §1.2.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.capability.domains import DOMAIN_PACKS
from core.capability.expert_demo import (
    ACCURACY_MIN,
    ALL_PASS_RATE_MIN,
    INTENT_ACCURACY_MIN,
    LANE_SHAPE_REGISTRY,
    REPLAY_DETERMINISM_MIN,
    SHAPE_CHECKERS,
    SURFACE_GROUNDEDNESS_MIN,
    TERM_CAPTURE_RATE_MIN,
    VERSOR_CLOSURE_RATE_MIN,
    evaluate_expert_demo,
    resolve_lane_shape,
)
from core.capability.reviewers import (
    ExpertDemoClaim,
    Reviewer,
    ReviewerRegistry,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _ratified_pack_lanes() -> set[str]:
    """Collect every lane id referenced by every ratified pack."""
    out: set[str] = set()
    for packs in DOMAIN_PACKS.values():
        for pack_id in packs:
            manifest_path = (
                _REPO_ROOT
                / "language_packs"
                / "data"
                / pack_id
                / "manifest.json"
            )
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest.get("eval_lanes", []) or []:
                lane = entry.get("lane")
                if isinstance(lane, str):
                    out.add(lane)
    return out


class TestLaneShapeExplicit:
    def test_every_ratified_lane_resolves_to_registered_shape(self) -> None:
        lanes = _ratified_pack_lanes()
        assert lanes, "expected at least one lane attached to a ratified pack"
        unresolved = [lane for lane in lanes if resolve_lane_shape(lane) is None]
        assert unresolved == [], (
            f"lanes referenced by ratified packs but missing from "
            f"LANE_SHAPE_REGISTRY: {sorted(unresolved)}"
        )


class TestShapeThresholdsAreNamed:
    def test_every_registered_shape_has_checker(self) -> None:
        shapes = set(LANE_SHAPE_REGISTRY.values())
        for shape_id in shapes:
            assert shape_id in SHAPE_CHECKERS, (
                f"shape {shape_id!r} appears in LANE_SHAPE_REGISTRY but has "
                f"no entry in SHAPE_CHECKERS"
            )

    def test_no_shape_without_a_lane(self) -> None:
        """Every shape with a checker must be used by at least one lane.

        Catches dead-shape drift: if a shape is removed from all lanes
        in the registry, the SHAPE_CHECKERS entry should also be retired
        by a follow-up ADR rather than left as silently-unused code.
        """
        used_shapes = set(LANE_SHAPE_REGISTRY.values())
        unused = set(SHAPE_CHECKERS.keys()) - used_shapes
        assert unused == set(), (
            f"shape checkers defined but no lane uses them: {sorted(unused)}"
        )


class TestUnknownLaneFailsClosed:
    def _registry_with_claim(self, lane_id: str) -> ReviewerRegistry:
        reviewer = Reviewer(
            reviewer_id="shay-j",
            display_name="Joshua Shay",
            role="primary",
            domains=("*",),
            review_scope=("pack", "proposal", "chain", "eval"),
            provenance="adr-0092:bootstrap:2026-05-21",
        )
        claim = ExpertDemoClaim(
            domain_id="mathematics_logic",
            evidence_lanes=(lane_id,),
            evidence_revision="rev1",
            signed_by="shay-j",
            claim_digest="a" * 64,
        )
        return ReviewerRegistry(
            schema_version=1, reviewers=(reviewer,), expert_demo_claims=(claim,)
        )

    def test_unregistered_lane_id_refuses(self) -> None:
        lane_id = "synthetic_unregistered_lane"
        registry = self._registry_with_claim(lane_id)
        verdict = evaluate_expert_demo(
            domain_id="mathematics_logic",
            reasoning_capable=True,
            registry=registry,
            domain_lanes=(lane_id,),
            lane_results={
                lane_id: {
                    "public": {"accuracy": 1.0},
                    "holdout": {"accuracy": 1.0},
                }
            },
        )
        assert verdict.passed is False
        assert "no registered shape" in verdict.reason

    def test_resolve_returns_none_for_unknown(self) -> None:
        assert resolve_lane_shape("definitely_not_a_real_lane") is None


class TestCognitionShapeUnchangedUnderAmendment:
    """ADR-0106 §1.2 thresholds must remain bit-identical post-ADR-0109."""

    def test_cognition_thresholds_unchanged(self) -> None:
        assert SURFACE_GROUNDEDNESS_MIN == 0.95
        assert TERM_CAPTURE_RATE_MIN == 0.85
        assert INTENT_ACCURACY_MIN == 0.95
        assert VERSOR_CLOSURE_RATE_MIN == 1.0

    def test_cognition_lane_resolves_to_cognition_shape(self) -> None:
        assert resolve_lane_shape("cognition") == "cognition_shape"


class TestShapeThresholdValues:
    """Pin the documented minimums per ADR-0109 §2."""

    def test_accuracy_shape_minimum(self) -> None:
        assert ACCURACY_MIN == 0.95

    def test_inference_shape_minimums(self) -> None:
        assert ALL_PASS_RATE_MIN == 0.95
        assert REPLAY_DETERMINISM_MIN == 1.0


class TestSymbolicLogicShapeGate:
    def test_symbolic_logic_resolves_to_inference_shape(self) -> None:
        assert resolve_lane_shape("symbolic_logic") == "inference_shape"

    def test_symbolic_logic_with_inference_metrics_passes(self) -> None:
        reviewer = Reviewer(
            reviewer_id="shay-j",
            display_name="Joshua Shay",
            role="primary",
            domains=("*",),
            review_scope=("pack", "proposal", "chain", "eval"),
            provenance="adr-0092:bootstrap:2026-05-21",
        )
        
        metrics = {
            "all_pass_rate": 0.98,
            "replay_determinism": 1.0,
            "overall_pass": True,
        }
        
        lane_results = {
            "symbolic_logic": {
                "public": metrics,
                "holdout": metrics,
            }
        }
        
        from core.capability.expert_demo import derive_evidence_digest
        digest = derive_evidence_digest(
            domain_id="systems_software",
            evidence_revision="rev1",
            evidence_lanes=("symbolic_logic",),
            lane_results=lane_results,
        )
        
        claim = ExpertDemoClaim(
            domain_id="systems_software",
            evidence_lanes=("symbolic_logic",),
            evidence_revision="rev1",
            signed_by="shay-j",
            claim_digest=digest,
        )
        
        registry = ReviewerRegistry(
            schema_version=1, reviewers=(reviewer,), expert_demo_claims=(claim,)
        )
        
        verdict = evaluate_expert_demo(
            domain_id="systems_software",
            reasoning_capable=True,
            registry=registry,
            domain_lanes=("symbolic_logic",),
            lane_results=lane_results,
        )
        assert verdict.passed is True
        assert verdict.reason == "all audit-passed predicates satisfied"


class TestInferenceShapeAcceptsSynonyms:
    def test_accepts_all_three_pass_rate_alone(self) -> None:
        from core.capability.expert_demo import _check_inference_shape
        ok, reason = _check_inference_shape(
            "symbolic_logic",
            {
                "all_three_pass_rate": 1.0,
                "replay_determinism": 1.0,
                "overall_pass": True,
            },
        )
        assert ok is True
        assert reason == ""

    def test_accepts_all_pass_rate_alone(self) -> None:
        from core.capability.expert_demo import _check_inference_shape
        ok, reason = _check_inference_shape(
            "inference_closure",
            {
                "all_pass_rate": 1.0,
                "replay_determinism": 1.0,
                "overall_pass": True,
            },
        )
        assert ok is True
        assert reason == ""

    def test_rejects_third_synonym(self) -> None:
        from core.capability.expert_demo import _check_inference_shape
        ok, reason = _check_inference_shape(
            "some_lane",
            {
                "foo_bar_rate": 1.0,
                "replay_determinism": 1.0,
                "overall_pass": True,
            },
        )
        assert ok is False
        assert "missing required metric 'all_pass_rate'" in reason

    def test_precedence_primary_key_wins(self) -> None:
        from core.capability.expert_demo import _check_inference_shape
        # Both keys are present: all_pass_rate is below threshold,
        # all_three_pass_rate is at threshold. The primary must win (fail).
        ok, reason = _check_inference_shape(
            "symbolic_logic",
            {
                "all_pass_rate": 0.90,
                "all_three_pass_rate": 1.0,
                "replay_determinism": 1.0,
                "overall_pass": True,
            },
        )
        assert ok is False
        assert "all_pass_rate=0.9 below threshold" in reason

