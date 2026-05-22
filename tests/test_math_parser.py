"""ADR-0115 Phase 1.3 — math word-problem parser invariants.

Pins five load-bearing invariants:

1. **All 5 seed cases parse byte-equal.** Every case in
   ``evals/gsm8k_parser_dev/cases.jsonl`` satisfies
   ``parse_problem(case["problem"]).canonical_bytes() ==
   graph_from_dict(case["ground_truth_graph"]).canonical_bytes()``.

2. **Determinism.** Parsing the same input twice produces byte-equal
   canonical output.

3. **Phase 1.3 exit criterion gate.** Parse correctness across the
   current dev set is ≥ 0.90 (≥45/50 when the full set lands; today
   5/5 = 1.00 on the seed set).

4. **Typed refusal on unsupported constructions.** Constructions out of
   scope per ADR-0115 §"Scope boundary" raise :class:`ParseError`
   rather than guessing or silently producing a wrong graph.

5. **No mutation of source artifacts.** Parser is pure: same input
   string yields the same output and does not touch any file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_parser import ParseError, parse_problem
from generate.math_problem_graph import MathProblemGraph, graph_from_dict


_REPO_ROOT = Path(__file__).resolve().parent.parent
_CASES_PATH = _REPO_ROOT / "evals" / "gsm8k_parser_dev" / "cases.jsonl"


def _load_cases() -> list[dict]:
    return [json.loads(line) for line in _CASES_PATH.read_text().splitlines() if line.strip()]


def _parse_correctness(cases: list[dict]) -> tuple[int, int, list[str]]:
    """Return (passed, total, failure_ids) for byte-equal parses."""
    passed = 0
    failed: list[str] = []
    for c in cases:
        try:
            got = parse_problem(c["problem"])
            want = graph_from_dict(c["ground_truth_graph"])
            if got.canonical_bytes() == want.canonical_bytes():
                passed += 1
            else:
                failed.append(c["id"])
        except ParseError:
            failed.append(c["id"])
    return passed, len(cases), failed


class TestSeedCasesParseByteEqual:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_parses_byte_equal_to_ground_truth(self, case: dict) -> None:
        got = parse_problem(case["problem"])
        want = graph_from_dict(case["ground_truth_graph"])
        assert got.canonical_bytes() == want.canonical_bytes(), (
            f"{case['id']}: parser output != ground truth\n"
            f"  got:  {got.as_json()}\n"
            f"  want: {want.as_json()}"
        )


class TestDeterminism:
    @pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
    def test_two_parses_produce_byte_equal_output(self, case: dict) -> None:
        a = parse_problem(case["problem"])
        b = parse_problem(case["problem"])
        assert a.canonical_bytes() == b.canonical_bytes()
        assert a == b


class TestPhase1_3ExitCriterion:
    """The exit criterion for Phase 1.3 is parse correctness ≥ 0.90.

    Today the dev set is the 5 seed cases (5/5 = 1.00). When Codex's
    Phase 1.2 PR lands with 45 more cases, this same gate runs against
    50 and must produce ≥ 45 passes to ship Phase 1.3.
    """

    def test_parse_correctness_meets_exit_criterion(self) -> None:
        cases = _load_cases()
        passed, total, failed = _parse_correctness(cases)
        ratio = passed / total
        assert ratio >= 0.90, (
            f"parse correctness {passed}/{total} = {ratio:.2%} below 0.90 "
            f"exit criterion; failing cases: {failed}"
        )


class TestParserRejectsMalformed:
    def test_empty_input_raises(self) -> None:
        with pytest.raises(ParseError):
            parse_problem("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ParseError):
            parse_problem("   \n\t  ")

    def test_no_question_raises(self) -> None:
        with pytest.raises(ParseError, match="exactly one question"):
            parse_problem("Sam has 5 apples. He buys 3 more.")

    def test_multiple_questions_raises(self) -> None:
        with pytest.raises(ParseError, match="exactly one question"):
            parse_problem(
                "Sam has 5 apples. How many does he have? How many does Tom have?"
            )

    def test_question_referencing_undefined_entity_raises(self) -> None:
        with pytest.raises(ParseError, match="undefined entity"):
            parse_problem("Sam has 5 apples. How many apples does Tom have?")

    def test_unsupported_construction_raises(self) -> None:
        # Conditional / time-modal is out of scope per ADR-0115 Phase 1.1.
        with pytest.raises(ParseError):
            parse_problem(
                "If Sam had 5 apples, how many apples does Sam have?"
            )


class TestParserIsPure:
    def test_does_not_mutate_input_string(self) -> None:
        text = "Sam has 5 apples. He buys 3 more. How many apples does Sam have?"
        before = text
        parse_problem(text)
        assert text == before

    def test_does_not_mutate_cases_file(self) -> None:
        before = _CASES_PATH.read_bytes()
        for c in _load_cases():
            try:
                parse_problem(c["problem"])
            except ParseError:
                pass
        after = _CASES_PATH.read_bytes()
        assert before == after


class TestParserOutputIsTyped:
    def test_returns_math_problem_graph(self) -> None:
        result = parse_problem(
            "Sam has 5 apples. He buys 3 more. How many apples does Sam have?"
        )
        assert isinstance(result, MathProblemGraph)
        assert "Sam" in result.entities
        assert result.unknown.entity == "Sam"
        assert result.unknown.unit == "apples"
