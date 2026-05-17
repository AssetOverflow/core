"""Phase 4 threshold characterization invariants (ADR-0024 follow-up).

These tests are diagnostic, not gates.  They pin the finding so a
future change that silently improves (or breaks) the geometric
separability is visible in test output.

Findings recorded:

  * Per-case the relation_blade DOES separate correct from incorrect
    candidates (all five v2 cases pass mechanism-isolation), so the
    blade construction is not geometrically blind.
  * But globally NO STATIC threshold delivers separation_quality ≥ 0.8.
    Blade norms vary across cases (~10x range), so the same threshold
    value means different things case-to-case.
  * Post-Phase-1 (ADR-0024 addendum): v1/dev cases were rewritten with
    pack-grounded tokens (e.g. tone/evidence/memory/wisdom), so the
    chain-token outer-product blade now constructs successfully (0/9
    skipped vs the pre-rewrite 9/9).  But the chain-blade geometry on
    v1/dev still does NOT separate cleanly (best_separation_quality
    ≈ 0.06), reinforcing the deeper Phase 4 finding: v1/dev chain
    blades probe teaching-driven walk (ADR-0022/0023), not the
    inner-loop's blade-admissibility mechanism.  v1/dev belong to the
    boundary-walk lane (runner.py); v2's seed_token + relation_blade_token
    schema is the proper inner-loop fixture.

ADR-0025 design implication: static thresholds (global, relation-typed,
or frame-derived) are insufficient.  Per-case normalized thresholds
(e.g. fraction of blade self-score) are the next thing to investigate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.forward_semantic_control.threshold_characterization import characterize

V1 = Path("evals/forward_semantic_control/public/v1/cases.jsonl")
V2 = Path("evals/forward_semantic_control/public/v2/cases.jsonl")
DEV = Path("evals/forward_semantic_control/dev/cases.jsonl")


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.fixture(scope="module")
def v1_report():
    cases = _load(V1) + _load(DEV)
    if not cases:
        pytest.skip("v1/dev corpus not available")
    return characterize(cases)


@pytest.fixture(scope="module")
def v2_report():
    cases = _load(V2)
    if not cases:
        pytest.skip("v2 corpus not available")
    return characterize(cases)


class TestV1ChainBladePostGrounding:
    """Post-Phase-1: v1/dev chain_tokens were rewritten with pack-grounded
    tokens (ADR-0024 addendum).  Region construction now succeeds — but
    the chain-blade geometry remains a poor fit for the inner-loop lane.
    These tests pin the new finding: v1/dev is constructible but probes
    a different mechanism than v2.
    """

    def test_no_v1_cases_skipped_after_grounding(self, v1_report) -> None:
        # Phase 1 retired synthetic chain tokens; every case now grounds.
        assert v1_report.metrics["skipped_count"] == 0

    def test_v1_chain_blade_geometry_remains_unsuitable(self, v1_report) -> None:
        # Constructible but not separable: chain-blade outer-product
        # geometry produces near-zero separation_quality on v1/dev,
        # confirming the architectural finding that v1/dev belong to
        # the boundary-walk lane, not the inner-loop lane.  If a future
        # change pushes this above 0.5, ADR-0024's lane-assignment
        # decision may need revisiting.
        assert v1_report.metrics["best_separation_quality"] < 0.5


class TestV2PerCaseSeparates:
    """Per-case, every v2 case has correct_min > incorrect_max."""

    def test_every_v2_case_separates_locally(self, v2_report) -> None:
        for detail in v2_report.case_details:
            if detail.get("skipped"):
                continue
            correct = detail["correct_scores"]
            incorrect = detail["incorrect_scores"]
            assert correct, f"case {detail.get('id')} has no correct candidate"
            assert min(correct) > max(incorrect), (
                f"case {detail.get('id')} fails local separation: "
                f"correct_min={min(correct)} ≤ incorrect_max={max(incorrect)}"
            )


class TestV2GlobalNonSeparability:
    """Despite per-case separability, no static threshold works
    globally — this is the load-bearing finding for ADR-0025."""

    def test_no_static_threshold_passes_gate(self, v2_report) -> None:
        # If a future change makes this pass, ADR-0025 design may
        # need revision.  Currently expected: False.
        assert v2_report.metrics["geometry_supports_static_threshold"] is False

    def test_score_distributions_overlap_globally(self, v2_report) -> None:
        overlap = v2_report.score_distributions["overlap"]
        # incorrect_max > correct_min ⇒ static threshold cannot
        # separate.  This is the geometric fact ADR-0025 must address.
        assert overlap["separable_by_static_threshold"] is False
        assert overlap["overlap_size"] > 0.0
