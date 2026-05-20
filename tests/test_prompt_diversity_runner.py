"""Prompt-diversity lane runner — contract pins.

Pins the v1 contract surface so future composer changes (ADR-0085) and
surface-vs-envelope work cannot silently break the measurement
instrument the contract is built around.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.framework import get_lane, run_lane
from evals.prompt_diversity.runner import (
    _classify_response_shape,
    _surface_has_audit_leak,
)


_PUBLIC_V1 = Path(__file__).resolve().parents[1] / "evals" / "prompt_diversity" / "public" / "v1" / "cases.jsonl"


def _load_public_cases() -> list[dict]:
    return [json.loads(line) for line in _PUBLIC_V1.read_text().splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# Shape classifier
# --------------------------------------------------------------------------- #


class TestShapeClassifier:
    @pytest.mark.parametrize(
        "surface,expected_shape,want",
        [
            ("Knowledge is justified true belief.", "predicate_identity", True),
            ("light reveals truth, which grounds knowledge", "explanation", True),
            ("First, observe. Then, infer.", "sequence", True),
            ("wisdom contrasts with judgment", "two_subject_contrast", True),
            ("No session evidence yet.", "honest_disclosure", True),
            ("knowledge, evidence, inference", "narrative", True),
            # Mismatch direction — chain-walk shape miscast as definition
            ("light reveals truth, which grounds knowledge", "predicate_identity", False),
        ],
    )
    def test_shape_classifier(self, surface: str, expected_shape: str, want: bool) -> None:
        assert _classify_response_shape(surface, expected_shape) is want

    def test_unknown_shape_defaults_pass(self) -> None:
        # Neutral pass for unknown shapes — protects against new
        # categories being penalised before the classifier is taught.
        assert _classify_response_shape("any text", "brand_new_shape") is True

    def test_empty_surface_fails(self) -> None:
        assert _classify_response_shape("", "predicate_identity") is False


# --------------------------------------------------------------------------- #
# Audit-leak detector
# --------------------------------------------------------------------------- #


class TestAuditLeak:
    @pytest.mark.parametrize(
        "surface,is_leak",
        [
            ("light — teaching-grounded (cognition_chains_v1): ...", True),
            ("light — pack-grounded (en_core_cognition_v1): ...", True),
            ("No session evidence yet.", True),
            # Bare semantic-domain tag in user surface
            ("cognition.illumination", True),
            ("logos.core; cognition.truth.", True),
            # Clean user-facing surfaces
            ("Light is the medium by which what exists becomes visible.", False),
            ("Knowledge requires evidence.", False),
            ("", False),
        ],
    )
    def test_leak_detection(self, surface: str, is_leak: bool) -> None:
        assert _surface_has_audit_leak(surface) is is_leak


# --------------------------------------------------------------------------- #
# End-to-end run on the v1 public split
# --------------------------------------------------------------------------- #


class TestPublicV1:
    """Pins the v1 contract surface against the public split.

    The lane has NO numeric pass thresholds at v1 by design (the
    contract is explicit about this).  The ONLY hard gate is
    ``versor_closure_rate == 1.00``.  Everything else is baseline
    distribution we measure against, not score for.
    """

    @pytest.fixture(scope="class")
    def lane_result(self) -> object:
        lane = get_lane("prompt_diversity")
        return run_lane(lane, version="v1", split="public")

    def test_lane_discoverable(self) -> None:
        lane = get_lane("prompt_diversity")
        assert "v1" in lane.versions

    def test_all_cases_run(self, lane_result) -> None:  # type: ignore[no-untyped-def]
        cases = _load_public_cases()
        assert lane_result.metrics["total"] == len(cases)
        assert len(lane_result.case_details) == len(cases)

    def test_versor_closure_invariant(self, lane_result) -> None:  # type: ignore[no-untyped-def]
        # The only numeric pass threshold at v1.  Per ADR / contract:
        # the algebra invariant must hold for every case the pipeline
        # accepts.
        assert lane_result.metrics["versor_closure_rate"] == 1.0

    def test_all_metrics_in_unit_interval(self, lane_result) -> None:  # type: ignore[no-untyped-def]
        for key in (
            "intent_accuracy",
            "versor_closure_rate",
            "response_shape_fit",
            "audit_in_surface_rate",
            "gloss_quote_rate",
        ):
            value = lane_result.metrics[key]
            assert 0.0 <= value <= 1.0, f"{key} out of unit interval: {value}"

    def test_breakdown_groups_present(self, lane_result) -> None:  # type: ignore[no-untyped-def]
        # Per-cell breakdown by (question_shape, sophistication, domain)
        # — the contract's "how to read the output" instructs callers
        # to look at distributions, not just aggregates.
        breakdown = lane_result.metrics["breakdown"]
        assert isinstance(breakdown, dict)
        assert breakdown, "breakdown is empty — runner did not aggregate cells"
        # Every cell must carry the four moveable per-cell metrics.
        for shape_cells in breakdown.values():
            for soph_cells in shape_cells.values():
                for cell in soph_cells.values():
                    assert {"n", "intent_accuracy", "response_shape_fit", "audit_in_surface_rate", "gloss_quote_rate"} <= cell.keys()

    def test_baseline_diversity(self, lane_result) -> None:  # type: ignore[no-untyped-def]
        # The lane's STATED failure mode (contract §When it has failed
        # and why): "if the distribution looks identical to the
        # cognition lane (i.e. the suite isn't actually diverse)".
        # Concretely: at least 5 distinct question_shape values and
        # at least 3 distinct domain values must appear in the case
        # details — otherwise the suite is overfitting the same way
        # the cognition lane does.
        details = lane_result.case_details
        shapes = {d["question_shape"] for d in details}
        domains = {d["domain"] for d in details}
        assert len(shapes) >= 5, f"only {len(shapes)} question shapes — suite is not diverse"
        assert len(domains) >= 3, f"only {len(domains)} domains — suite is not diverse"
