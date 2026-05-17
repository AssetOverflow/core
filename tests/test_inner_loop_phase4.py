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
  * The v1 chain-token outer-product blade is ungrounded in the active
    pack — all 9 cases are skipped because chain_tokens (alpha, beta,
    gamma, delta) are not in the en_core_cognition vocab.  This is its
    own load-bearing finding for ADR-0025: chain-token blades are
    unsuitable as the default region construction.

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


class TestV1ChainBladeUngrounded:
    """V1 chain_tokens are synthetic (alpha, beta, gamma, delta) and
    not present in the active pack.  The characterization should
    surface this by skipping every case.
    """

    def test_all_v1_cases_skipped(self, v1_report) -> None:
        assert v1_report.metrics["skipped_count"] == v1_report.metrics["case_count"]

    def test_v1_reports_no_separation(self, v1_report) -> None:
        # No candidates ⇒ best_separation_quality stays at zero.
        assert v1_report.metrics["best_separation_quality"] == 0.0


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
