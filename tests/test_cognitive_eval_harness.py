"""Tests for the cognitive eval harness."""

from __future__ import annotations

import json
from pathlib import Path

from evals.run_cognition_eval import load_cases, run_eval, check_determinism


_CASES_PATH = Path(__file__).resolve().parent.parent / "evals" / "cognition_cases.jsonl"


class TestCognitionEvalLoadsCases:
    def test_loads_all_cases(self) -> None:
        cases = load_cases(_CASES_PATH)
        assert len(cases) >= 15
        assert all("id" in c for c in cases)
        assert all("prompt" in c for c in cases)
        assert all("expected_intent" in c for c in cases)

    def test_cases_have_valid_structure(self) -> None:
        cases = load_cases(_CASES_PATH)
        for case in cases:
            assert isinstance(case["id"], str)
            assert isinstance(case["prompt"], str)
            assert case["expected_intent"] in {
                "definition", "comparison", "cause", "procedure",
                "recall", "correction", "verification", "unknown",
            }
            assert isinstance(case.get("expected_terms", []), list)

    def test_cases_cover_required_categories(self) -> None:
        cases = load_cases(_CASES_PATH)
        categories = {c.get("category", "unknown") for c in cases}
        required = {"definition", "comparison", "cause", "correction", "verification", "unknown"}
        assert required.issubset(categories), f"missing: {required - categories}"


class TestCognitionEvalRunsSmallCaseSet:
    def test_runs_single_case(self) -> None:
        cases = load_cases(_CASES_PATH)[:1]
        report = run_eval(cases)
        assert report.total == 1
        assert len(report.cases) == 1
        assert report.cases[0].case_id == cases[0]["id"]

    def test_runs_five_cases(self) -> None:
        cases = load_cases(_CASES_PATH)[:5]
        report = run_eval(cases)
        assert report.total == 5
        assert len(report.cases) == 5


class TestCognitionEvalRecordsIntentAccuracy:
    def test_definition_intent_detected(self) -> None:
        cases = [c for c in load_cases(_CASES_PATH) if c["expected_intent"] == "definition"][:2]
        report = run_eval(cases)
        assert report.intent_correct == report.total

    def test_comparison_intent_detected(self) -> None:
        cases = [c for c in load_cases(_CASES_PATH) if c["expected_intent"] == "comparison"][:1]
        report = run_eval(cases)
        assert report.intent_correct == report.total

    def test_report_has_accuracy_metric(self) -> None:
        cases = load_cases(_CASES_PATH)[:3]
        report = run_eval(cases)
        assert 0.0 <= report.intent_accuracy <= 1.0
        report_dict = report.as_dict()
        assert "intent_accuracy" in report_dict


class TestCognitionEvalRecordsTraceHashes:
    def test_trace_hashes_present(self) -> None:
        cases = load_cases(_CASES_PATH)[:3]
        report = run_eval(cases)
        assert len(report.trace_hashes) == 3
        for case_id, h in report.trace_hashes.items():
            assert isinstance(h, str)
            assert len(h) == 64  # SHA-256 hex

    def test_distinct_cases_get_distinct_hashes(self) -> None:
        cases = load_cases(_CASES_PATH)[:5]
        report = run_eval(cases)
        hashes = list(report.trace_hashes.values())
        assert len(set(hashes)) == len(hashes), "duplicate trace hashes"


class TestCognitionEvalIsDeterministic:
    def test_two_runs_same_hashes(self) -> None:
        cases = load_cases(_CASES_PATH)[:3]
        assert check_determinism(cases, runs=2)


class TestEvalReportSerialization:
    def test_as_dict_roundtrips(self) -> None:
        cases = load_cases(_CASES_PATH)[:2]
        report = run_eval(cases)
        d = report.as_dict()
        serialized = json.dumps(d)
        parsed = json.loads(serialized)
        assert parsed["total"] == 2
        assert "intent_accuracy" in parsed
        assert "trace_hashes" in parsed
        assert len(parsed["cases"]) == 2
