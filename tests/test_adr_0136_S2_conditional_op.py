"""ADR-0136.S.2 — Conditional-op question tests.

Pins the new `extract_conditional_op_question_candidates` extractor and
the short-circuit path in `parse_and_solve` for the shape:

    "If <Entity> <verb> <N> <unit>, how many <unit2> does <Entity2> <aux>
     [left|now|remaining|...]?"
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import (
    _COND_ADD_VERBS,
    _COND_SUBTRACT_VERBS,
    extract_conditional_op_question_candidates,
)


_REPO = Path(__file__).resolve().parent.parent


# ── Regex extractor tests ────────────────────────────────────────────


class TestConditionalOpExtractor:
    def test_subtract_canonical(self) -> None:
        cands = extract_conditional_op_question_candidates(
            "If Ella sells 200 apples, how many apples does Ella has left?"
        )
        assert len(cands) == 1
        c = cands[0]
        assert c.entity == "Ella"
        assert c.op == "subtract"
        assert c.operand == 200.0
        assert c.unit == "apples"

    def test_add_canonical(self) -> None:
        cands = extract_conditional_op_question_candidates(
            "If Bob buys 5 apples, how many apples does Bob have now?"
        )
        assert len(cands) == 1
        c = cands[0]
        assert c.op == "add"
        assert c.operand == 5.0

    @pytest.mark.parametrize(
        "verb", ["sells", "gives", "eats", "uses", "loses", "spends", "donates"]
    )
    def test_subtract_verbs(self, verb: str) -> None:
        cands = extract_conditional_op_question_candidates(
            f"If Alice {verb} 3 apples, how many apples does Alice have left?"
        )
        assert len(cands) == 1
        assert cands[0].op == "subtract"

    @pytest.mark.parametrize(
        "verb", ["buys", "gets", "receives", "finds", "collects", "earns"]
    )
    def test_add_verbs(self, verb: str) -> None:
        cands = extract_conditional_op_question_candidates(
            f"If Alice {verb} 3 apples, how many apples does Alice have now?"
        )
        assert len(cands) == 1
        assert cands[0].op == "add"

    def test_unit_mismatch_refuses(self) -> None:
        cands = extract_conditional_op_question_candidates(
            "If Ella sells 200 apples, how many oranges does Ella have left?"
        )
        assert cands == []

    def test_entity_mismatch_refuses(self) -> None:
        cands = extract_conditional_op_question_candidates(
            "If Ella sells 200 apples, how many apples does Bob have left?"
        )
        assert cands == []

    def test_unknown_verb_refuses(self) -> None:
        cands = extract_conditional_op_question_candidates(
            "If Ella juggles 200 apples, how many apples does Ella have left?"
        )
        assert cands == []

    def test_zero_operand_refuses(self) -> None:
        cands = extract_conditional_op_question_candidates(
            "If Ella sells 0 apples, how many apples does Ella have left?"
        )
        assert cands == []

    def test_verb_sets_disjoint(self) -> None:
        assert _COND_SUBTRACT_VERBS.isdisjoint(_COND_ADD_VERBS)


# ── End-to-end short-circuit tests ───────────────────────────────────


class TestConditionalOpEndToEnd:
    def test_gsm8k_0042_admits_30(self) -> None:
        """The proof case for S.2."""
        r = parse_and_solve(
            "Ella has 4 bags with 20 apples in each bag and "
            "six bags with 25 apples in each bag.  "
            "If Ella sells 200 apples, how many apples does Ella has left?"
        )
        assert r.answer == 30.0, f"got {r.answer} ({r.refusal_reason})"

    def test_simple_subtract(self) -> None:
        r = parse_and_solve(
            "Bob has 100 apples.  "
            "If Bob eats 30 apples, how many apples does Bob have left?"
        )
        assert r.answer == 70.0

    def test_simple_add(self) -> None:
        r = parse_and_solve(
            "Alice has 12 apples.  "
            "If Alice buys 8 apples, how many apples does Alice have now?"
        )
        assert r.answer == 20.0

    def test_negative_result_refuses(self) -> None:
        """Selling more than you have must refuse (never produce negative)."""
        r = parse_and_solve(
            "Bob has 10 apples.  "
            "If Bob sells 50 apples, how many apples does Bob have left?"
        )
        assert r.answer is None

    def test_no_matching_initial_state_refuses(self) -> None:
        """Question about apples but no initial-state apples → refuse."""
        r = parse_and_solve(
            "Bob has 10 oranges.  "
            "If Bob sells 5 apples, how many apples does Bob have left?"
        )
        assert r.answer is None

    def test_no_matching_entity_refuses(self) -> None:
        r = parse_and_solve(
            "Bob has 100 apples.  "
            "If Alice sells 30 apples, how many apples does Alice have left?"
        )
        assert r.answer is None


# ── B3 + S.1 regression guards ───────────────────────────────────────


def test_b3_lane_still_passes() -> None:
    from evals.math_bounded_grammar.v1.runner import build_report, load_cases

    cases_path = _REPO / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
    report = build_report(load_cases(cases_path))
    assert report["metrics"]["wrong"] == 0


def test_s1_axis_lane_still_passes() -> None:
    from evals.math_capability_axes.S1_rate_events.v1.runner import build_report

    report = build_report()
    assert report["metrics"]["wrong"] == 0


# ── GSM8K safety rail ────────────────────────────────────────────────


def test_gsm8k_post_s2_admission_honest() -> None:
    """Post-S.2: 3 admissions expected (0014, 0018, 0042); wrong stays 0."""
    cases = [
        json.loads(line)
        for line in (
            _REPO / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    admitted: list[str] = []
    wrong: list[tuple[str, float, float]] = []
    for c in cases:
        r = parse_and_solve(c["question"])
        if r.answer is not None:
            if r.answer == c["answer_numeric"]:
                admitted.append(c["case_id"])
            else:
                wrong.append((c["case_id"], r.answer, c["answer_numeric"]))
    assert wrong == [], f"wrong admissions: {wrong}"
    assert "gsm8k-train-sample-v1-0014" in admitted  # S.1 capacity
    assert "gsm8k-train-sample-v1-0018" in admitted  # S.1 inverted
    assert "gsm8k-train-sample-v1-0042" in admitted  # S.2 cond-op
    assert len(admitted) >= 3
