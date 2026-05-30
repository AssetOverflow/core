"""ADR-0131.3 — Bounded-grammar word-problem lane invariants.

Asserts 6 load-bearing invariants for the B3 math expert benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.math_bounded_grammar.v1.runner import build_report, load_cases
from generate.math_parser import ParseError, parse_problem
from generate.math_problem_graph import VALID_OPERATION_KINDS, MathProblemGraph

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
_CASES_PATH = _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
_REPORT_PATH = _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "report.json"


@pytest.fixture
def cases() -> list[dict]:
    return load_cases(_CASES_PATH)


class TestDatasetIntegrity:
    """Invariant 1: Unique IDs, expected outcomes, and shape categories."""

    def test_case_ids_are_unique(self, cases: list[dict]) -> None:
        case_ids = [c["case_id"] for c in cases]
        assert len(case_ids) == len(set(case_ids)), "Duplicate case_id found"

    def test_expected_outcomes_are_valid(self, cases: list[dict]) -> None:
        valid_outcomes = {"solved_correct", "solved_wrong", "refused"}
        for c in cases:
            assert (
                c["expected"] in valid_outcomes
            ), f"Invalid expected outcome in {c['case_id']}: {c['expected']}"

    def test_shape_categories_are_valid(self, cases: list[dict]) -> None:
        valid_shapes = {
            "canonical_has_buys",
            "there_are_count",
            "substance_qualifier",
            "compare_additive",
            "compare_multiplicative",
            "transfer",
            "multiply",
            "divide",
            "apply_rate",
            "refused_paraphrase",
            "refused_unit",
            "refused_ambiguous",
            "refused_multistep",
        }
        for c in cases:
            assert (
                c["shape_category"] in valid_shapes
            ), f"Invalid shape_category in {c['case_id']}: {c['shape_category']}"


class TestGrammarClosure:
    """Invariant 2: Happy paths parse; refused paths raise typed refusal at parser level."""

    def test_solved_correct_and_solved_wrong_parse_successfully(
        self, cases: list[dict]
    ) -> None:
        for c in cases:
            if c["expected"] in ("solved_correct", "solved_wrong"):
                try:
                    graph = parse_problem(c["problem"])
                    assert isinstance(graph, MathProblemGraph)
                except ParseError as exc:
                    pytest.fail(
                        f"Expected {c['case_id']} to parse, but it raised ParseError: {exc}"
                    )

    def test_refused_cases_raise_typed_refusal_at_parser_level(
        self, cases: list[dict]
    ) -> None:
        for c in cases:
            if c["expected"] == "refused":
                # Some refused cases might parse but fail solver (like division by zero),
                # but most must raise ParseError directly. Let's assert at the parser level
                # where expected by design, or check they fail cleanly.
                if c["shape_category"] == "refused_multistep":
                    # e.g. division by zero parses but fails solver
                    continue
                with pytest.raises(ParseError) as exc:
                    parse_problem(c["problem"])
                # Confirm we get a typed ParseError
                assert exc.type is ParseError


class TestExitCriterion:
    """Invariant 3: wrong == 0, correct_rate >= 0.95."""

    def test_report_satisfies_exit_criterion(self, cases: list[dict]) -> None:
        report = build_report(cases)
        metrics = report["metrics"]
        assert (
            metrics["wrong"] == 0
        ), f"wrong count must be strictly 0, got {metrics['wrong']}"
        assert metrics["correct_rate"] >= 0.95, (
            f"correct_rate {metrics['correct_rate']:.2%} below 0.95 "
            "exit criterion"
        )
        assert report["exit_criterion"]["passed"] is True


class TestReplayDeterminism:
    """Invariant 4: report.json byte-equality across runs."""

    def test_two_consecutive_reports_are_byte_equal(self, cases: list[dict]) -> None:
        r1 = build_report(cases)
        r2 = build_report(cases)

        # Build JSON strings with compact separators
        s1 = json.dumps(r1, sort_keys=True, separators=(",", ":"))
        s2 = json.dumps(r2, sort_keys=True, separators=(",", ":"))
        assert s1 == s2


class TestClassDiversity:
    """Invariant 5: At least one case of each class."""

    def test_all_expected_classes_represented(self, cases: list[dict]) -> None:
        classes = {c["expected"] for c in cases}
        assert classes == {"solved_correct", "solved_wrong", "refused"}


class TestOperationKindCoverage:
    """Invariant 6: All 8 operation kinds exercised by solved_correct cases."""

    def test_all_operation_kinds_covered(self, cases: list[dict]) -> None:
        exercised_kinds = set()
        for c in cases:
            if c["expected"] == "solved_correct":
                graph = parse_problem(c["problem"])
                for op in graph.operations:
                    exercised_kinds.add(op.kind)

        # The unknown resolution might also contain total summation (entity=None),
        # but operations cover the main kinds. ADR-0190 — ``partition`` is
        # exercised by gsm8k train_sample 0046 + the dedicated partition
        # round-trip/solver/verifier tests, not this legacy curated lane;
        # exempt it here rather than overfit the bounded-grammar corpus.
        kinds_required_in_lane = VALID_OPERATION_KINDS - {"partition"}
        assert kinds_required_in_lane.issubset(exercised_kinds), (
            f"VALID_OPERATION_KINDS {kinds_required_in_lane} not subset of "
            f"exercised kinds {exercised_kinds}"
        )
