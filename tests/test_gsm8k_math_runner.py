"""ADR-0119.3 — gsm8k_math lane runner invariants.

Pins five load-bearing invariants:

1. **Determinism (ADR-0114a Obligation #9).** Same case list →
   byte-equal :class:`LaneReport.canonical_bytes()`.

2. **Outcome categorization is exhaustive.** Every case lands in
   exactly one of ``correct`` / ``wrong`` / ``refused``.

3. **Zero-wrong gate (ADR-0114a Obligation #4).** On the existing
   parser dev set (gpd-001..050, where all 50 cases verify with
   the on-main pipeline), the runner produces ``wrong == 0``.

4. **Refusal is first-class.** A graph that triggers SolveError
   (e.g. division by zero) produces ``outcome == "refused"`` with a
   reason that names the solver.

5. **Correct outcomes carry full audit trail.** Every ``correct``
   case has trace_hash + realized_prose set; every ``refused`` case
   has trace_hash / realized_prose either None or set per spec.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.gsm8k_math.runner import CaseOutcome, LaneReport, run_lane


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# Use gpd-001..050 as a known-good case set (already on main; 50/50 verify)
_GPD_CASES = _load_jsonl(_REPO_ROOT / "evals" / "gsm8k_parser_dev" / "cases.jsonl")


class TestDeterminism:
    def test_two_runs_produce_byte_equal_report(self) -> None:
        r1 = run_lane(_GPD_CASES)
        r2 = run_lane(_GPD_CASES)
        assert r1.canonical_bytes() == r2.canonical_bytes()


class TestOutcomeCategorizationIsExhaustive:
    def test_every_case_lands_in_one_outcome(self) -> None:
        report = run_lane(_GPD_CASES)
        total = report.metrics["cases_total"]
        correct = report.metrics["correct"]
        wrong = report.metrics["wrong"]
        refused = report.metrics["refused"]
        decoded = report.metrics["decoded_unarticulated"]
        assert correct + wrong + refused + decoded == total
        assert total == len(_GPD_CASES)

    def test_each_case_detail_has_recognized_outcome(self) -> None:
        report = run_lane(_GPD_CASES)
        for detail in report.case_details:
            assert detail["outcome"] in {"correct", "wrong", "refused", "decoded_unarticulated"}


class TestZeroWrongOnKnownGoodCases:
    """The gpd-001..050 dev set is fully exercised on main today.

    ADR-0114a Obligation #4: ``wrong == 0`` is the gate. The runner
    must reflect that on known-good cases.
    """

    def test_wrong_count_is_zero_on_gpd_dev_set(self) -> None:
        report = run_lane(_GPD_CASES)
        assert report.metrics["wrong"] == 0, (
            f"wrong={report.metrics['wrong']} on gpd dev set; "
            f"details: {[d for d in report.case_details if d['outcome'] == 'wrong']}"
        )

    def test_wrong_count_is_zero_gate_flag(self) -> None:
        report = run_lane(_GPD_CASES)
        assert report.metrics["wrong_count_is_zero"] is True

    def test_overall_pass_holds_when_no_wrong(self) -> None:
        report = run_lane(_GPD_CASES)
        assert report.metrics["overall_pass"] is True


class TestRefusalIsFirstClass:
    def test_unsupported_grammar_produces_refused(self) -> None:
        # "If" clause is out of scope per ADR-0115 §Phase 1.1 boundary;
        # parser raises ParseError → runner classifies as refused.
        case = {
            "id": "synthetic-refuse-01",
            "problem": "If Sam had 5 apples, how many would he have?",
            "expected_answer": 5,
            "expected_unit": "apples",
        }
        report = run_lane([case])
        assert report.metrics["refused"] == 1
        assert report.metrics["wrong"] == 0
        outcome = report.case_details[0]
        assert outcome["outcome"] == "refused"
        assert "parser" in outcome["reason"]

    def test_empty_input_produces_refused(self) -> None:
        case = {
            "id": "synthetic-refuse-02",
            "problem": "",
            "expected_answer": 0,
            "expected_unit": "apples",
        }
        report = run_lane([case])
        assert report.metrics["refused"] == 1
        assert report.metrics["wrong"] == 0


class TestWrongDetectedWhenAnswerMismatches:
    """If we deliberately mis-author a case (wrong expected_answer),
    the runner should report ``wrong``, not ``correct`` — proving the
    answer-comparison gate is actually load-bearing."""

    def test_mismatched_expected_answer_produces_wrong(self) -> None:
        # gpd-001's actual answer is 8 apples. Plant a wrong expected.
        case = dict(_GPD_CASES[0])
        case["id"] = "synthetic-wrong-01"
        case["expected_answer"] = 9999  # deliberately wrong
        report = run_lane([case])
        assert report.metrics["wrong"] == 1
        assert report.metrics["wrong_count_is_zero"] is False
        assert report.metrics["overall_pass"] is False
        outcome = report.case_details[0]
        assert outcome["outcome"] == "wrong"
        assert "answer mismatch" in outcome["reason"]

    def test_mismatched_expected_unit_produces_wrong(self) -> None:
        case = dict(_GPD_CASES[0])
        case["id"] = "synthetic-wrong-02"
        case["expected_unit"] = "bananas"  # wrong unit
        report = run_lane([case])
        assert report.metrics["wrong"] == 1
        outcome = report.case_details[0]
        assert outcome["outcome"] == "wrong"
        assert "unit mismatch" in outcome["reason"]


class TestCorrectOutcomeCarriesAuditTrail:
    def test_correct_case_has_trace_hash_and_prose(self) -> None:
        report = run_lane([_GPD_CASES[0]])
        outcome = report.case_details[0]
        assert outcome["outcome"] == "correct"
        assert outcome["trace_hash"] is not None
        assert len(outcome["trace_hash"]) == 64  # sha256 hex
        assert outcome["realized_prose"] is not None
        assert _GPD_CASES[0]["problem"].split(".")[0].split()[0] in outcome["realized_prose"]


class TestLaneReportShape:
    def test_report_is_conformant_lane_report(self) -> None:
        report = run_lane(_GPD_CASES[:3])
        assert isinstance(report, LaneReport)
        assert hasattr(report, "metrics")
        assert hasattr(report, "case_details")

    def test_metrics_keys_match_documented_schema(self) -> None:
        report = run_lane(_GPD_CASES[:3])
        expected_keys = {
            "cases_total",
            "correct",
            "wrong",
            "refused",
            "decoded_unarticulated",
            "correct_rate",
            "wrong_rate",
            "refused_rate",
            "decoded_unarticulated_rate",
            "wrong_count_is_zero",
            "overall_pass",
        }
        assert set(report.metrics.keys()) == expected_keys
