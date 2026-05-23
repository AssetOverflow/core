"""ADR-0131.1 — lane ratification tests.

The load-bearing assertion: the v1 benchmark lane passes its exit
criterion (correct_rate >= 0.95, wrong == 0) on the curated dataset
in evals/math_symbolic_equivalence/v1/cases.jsonl.

If this test fails, either the normalizer regressed or the dataset
was edited to include a case the v1 scope cannot handle. Both
require explicit operator review.
"""

from __future__ import annotations

import json
from pathlib import Path

from evals.math_symbolic_equivalence.v1.runner import (
    _load_cases,
    build_report,
)


_CASES_PATH = (
    Path(__file__).resolve().parent.parent
    / "evals"
    / "math_symbolic_equivalence"
    / "v1"
    / "cases.jsonl"
)


class TestDatasetIntegrity:
    def test_cases_file_exists(self) -> None:
        assert _CASES_PATH.exists(), f"missing dataset: {_CASES_PATH}"

    def test_cases_are_well_formed(self) -> None:
        cases = _load_cases()
        assert len(cases) >= 30, "v1 must ship at least 30 cases"
        for c in cases:
            for k in (
                "case_id", "expression_a", "expression_b",
                "expected", "category", "provenance",
            ):
                assert k in c, f"case {c.get('case_id')} missing field {k!r}"
            assert c["expected"] in ("equivalent", "not_equivalent", "refused")

    def test_no_duplicate_case_ids(self) -> None:
        cases = _load_cases()
        ids = [c["case_id"] for c in cases]
        assert len(ids) == len(set(ids)), "duplicate case_ids in dataset"

    def test_provenance_cites_adr(self) -> None:
        cases = _load_cases()
        for c in cases:
            assert "adr-0131" in c["provenance"]


class TestLaneGate:
    def test_lane_passes_exit_criterion(self) -> None:
        cases = _load_cases()
        report = build_report(cases)
        assert report["exit_criterion"]["passed"], (
            f"lane gate failed: counts={report['counts']!r} "
            f"correct_rate={report['correct_rate']!r}"
        )

    def test_wrong_count_is_zero(self) -> None:
        # The wrong == 0 invariant is the load-bearing safety property.
        cases = _load_cases()
        report = build_report(cases)
        assert report["counts"]["wrong"] == 0, (
            "wrong count must be zero on the v1 dataset; per-case "
            f"detail: {[c for c in report['per_case'] if c['verdict_class']=='wrong']}"
        )

    def test_refused_cases_have_expected_refused(self) -> None:
        # Every refusal in the result must correspond to a case whose
        # expected verdict was 'refused' (out-of-scope by design). If
        # we refuse on a case that expected a definite answer, that's
        # a regression of the normalizer's coverage.
        cases = _load_cases()
        report = build_report(cases)
        for entry in report["per_case"]:
            if entry["verdict_class"] == "refused":
                assert entry["expected"] == "refused", (
                    f"engine refused on case {entry['case_id']} whose "
                    f"expected verdict was {entry['expected']!r}; "
                    f"reason: {entry['reason']}"
                )


class TestDeterminism:
    def test_report_is_byte_equal_across_runs(self) -> None:
        cases = _load_cases()
        r1 = build_report(cases)
        r2 = build_report(cases)
        s1 = json.dumps(r1, sort_keys=True).encode("utf-8")
        s2 = json.dumps(r2, sort_keys=True).encode("utf-8")
        assert s1 == s2
