"""Phase 3 mechanism-isolation invariants (ADR-0024 v2 corpus).

These tests are the *load-bearing* proof contract: in synthetic
cases designed to exercise the rejection mechanism, the inner loop
must (a) actually reject the forbidden decoy, (b) select the
expected endpoint instead, and (c) leave a causal trail in
``rejected_attempts``.

Pass criteria are stricter than Phase 2 (which is observational):
Phase 3 *gates* on ``mechanism_isolated``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.forward_semantic_control.v2_runner import run_lane

V2_CORPUS = Path("evals/forward_semantic_control/public/v2/cases.jsonl")


@pytest.fixture(scope="module")
def v2_report():
    if not V2_CORPUS.exists():
        pytest.skip("V2 corpus not available")
    with V2_CORPUS.open() as fh:
        cases = [json.loads(line) for line in fh if line.strip()]
    if not cases:
        pytest.skip("V2 corpus is empty")
    return run_lane(cases)


class TestMechanismIsolated:
    def test_mechanism_isolated_overall(self, v2_report) -> None:
        """The headline gate — every v2 case must isolate the mechanism."""
        assert v2_report.metrics["mechanism_isolated"] is True

    def test_pass_rate_is_one(self, v2_report) -> None:
        assert v2_report.metrics["pass_rate"] == 1.0

    def test_boundary_picks_decoy_every_case(self, v2_report) -> None:
        """If boundary doesn't pick the decoy on a v2 case, the case
        is mis-constructed — the mechanism never gets exercised."""
        assert v2_report.metrics["boundary_decoy_rate"] == 1.0

    def test_rejection_causally_traced_every_case(self, v2_report) -> None:
        """The forbidden token must appear in rejected_attempts on
        every case — this is the visible causal evidence."""
        assert v2_report.metrics["rejection_traced_rate"] == 1.0


class TestPerCaseInvariants:
    def test_no_case_was_skipped(self, v2_report) -> None:
        assert v2_report.metrics["skipped_count"] == 0

    def test_every_case_passed(self, v2_report) -> None:
        for detail in v2_report.case_details:
            assert detail.get("passed") is True, (
                f"Case {detail.get('id')} failed: "
                f"boundary={detail.get('boundary_selected')} "
                f"inner={detail.get('inner_selected')} "
                f"forbidden_traced={detail.get('rejection_in_trace')} "
                f"inner_exhausted={detail.get('inner_exhausted')}"
            )

    def test_inner_selection_matches_expected_endpoint(self, v2_report) -> None:
        for detail in v2_report.case_details:
            assert detail.get("inner_selected") == detail.get("expected_endpoint")

    def test_boundary_selection_matches_forbidden_token(self, v2_report) -> None:
        for detail in v2_report.case_details:
            assert detail.get("boundary_selected") == detail.get("forbidden_token")
