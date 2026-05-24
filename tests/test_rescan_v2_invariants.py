"""ADR-0136.S.2-post-rescan — invariant tests for barrier-shift ledger.

Pins: wrong==0, admission regression set, determinism, taxonomy completeness,
and closed barrier vocabulary.
"""

from __future__ import annotations

import json

import pytest

from evals.gsm8k_math.train_sample.v1.rescan_v2 import build_rescan

_REQUIRED_ADMISSIONS = {
    "gsm8k-train-sample-v1-0014",
    "gsm8k-train-sample-v1-0018",
    "gsm8k-train-sample-v1-0042",
}

_CLOSED_BARRIER_ENUM = {
    "admitted",
    "capacity_rate",
    "complex_question",
    "compound_comparative",
    "compound_multi_event",
    "compound_statement",
    "conditional_branch",
    "conditional_question",
    "context_filler",
    "distributive_each_actor",
    "distributive_multiply",
    "fraction_operand",
    "goal_statement",
    "multi_attribute_accumulation",
    "multi_day_accumulation",
    "multi_entity_initial",
    "novel_initial_form",
    "novel_initial_verb",
    "partition_divide",
    "percentage_rate",
    "rate_earnings",
    "rate_price",
    "temporal_age_anchor",
    "temporal_frequency",
}


@pytest.fixture(scope="module")
def rescan_result() -> tuple[list[dict], list[dict]]:
    return build_rescan()


class TestWrongIsZero:
    def test_no_wrong_admissions(self, rescan_result: tuple) -> None:
        rescan, _ = rescan_result
        for r in rescan:
            if r["current_outcome"] == "admitted":
                assert r["current_refusal_reason"] is None or r["current_refusal_reason"] == ""


class TestAdmissionRegression:
    def test_required_admissions_present(self, rescan_result: tuple) -> None:
        rescan, _ = rescan_result
        admitted = {
            r["case_id"] for r in rescan if r["current_outcome"] == "admitted"
        }
        assert admitted >= _REQUIRED_ADMISSIONS, (
            f"Missing required admissions: {_REQUIRED_ADMISSIONS - admitted}"
        )


class TestDeterminism:
    def test_rescan_byte_equal_across_runs(self) -> None:
        r1, t1 = build_rescan()
        r2, t2 = build_rescan()
        s1 = json.dumps(r1, indent=2, sort_keys=True)
        s2 = json.dumps(r2, indent=2, sort_keys=True)
        assert s1 == s2, "rescan records not deterministic"
        s3 = json.dumps(t1, indent=2, sort_keys=True)
        s4 = json.dumps(t2, indent=2, sort_keys=True)
        assert s3 == s4, "taxonomy records not deterministic"


class TestTaxonomyCompleteness:
    def test_taxonomy_has_50_entries(self, rescan_result: tuple) -> None:
        _, taxonomy = rescan_result
        assert len(taxonomy) == 50

    def test_all_barriers_in_closed_enum(self, rescan_result: tuple) -> None:
        _, taxonomy = rescan_result
        for entry in taxonomy:
            assert entry["primary_barrier"] in _CLOSED_BARRIER_ENUM, (
                f"{entry['case_id']}: barrier {entry['primary_barrier']!r} "
                f"not in closed enum"
            )

    def test_rescan_barriers_match_taxonomy(self, rescan_result: tuple) -> None:
        rescan, taxonomy = rescan_result
        for r, t in zip(rescan, taxonomy):
            assert r["case_id"] == t["case_id"]
            assert r["current_primary_barrier"] == t["primary_barrier"]
