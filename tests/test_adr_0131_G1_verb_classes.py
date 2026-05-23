"""ADR-0131.G.1 — G1 state-introducing verb classes capability tests.

Checks the invariants, safety rail (wrong == 0), and verb coverage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.math_capability_axes.G1_verb_classes.v1.runner import build_report, _load_cases, _CASES_PATH
from generate.math_candidate_parser import extract_initial_candidates, CandidateInitial
from generate.math_candidate_graph import parse_and_solve


@pytest.fixture(scope="module")
def cases() -> list[dict]:
    return _load_cases(_CASES_PATH)


@pytest.fixture(scope="module")
def report(cases) -> dict:
    return build_report(cases)


class TestG1DatasetIntegrity:
    def test_case_ids_are_unique(self, cases) -> None:
        case_ids = [c["case_id"] for c in cases]
        assert len(case_ids) == len(set(case_ids))

    def test_expected_outcomes_are_valid(self, cases) -> None:
        valid_outcomes = {"solved_correct", "solved_wrong", "refused"}
        for c in cases:
            assert c["expected"] in valid_outcomes


class TestG1SafetyRail:
    def test_wrong_count_is_zero(self, report) -> None:
        assert report["counts"]["wrong"] == 0
        assert report["exit_criterion"]["passed"] is True

    def test_every_verb_has_passing_case(self) -> None:
        verbs = [
            ("Sam buys 5 apples. How many apples does Sam have?", 5.0, "apples"),
            ("Sam bought 10 candies. How many candies does Sam have?", 10.0, "candies"),
            ("Sam sells 3 books. Tom has 5 books. How many books does Tom have?", 5.0, "books"),
            ("Sam collected 8 marbles. How many marbles does Sam have?", 8.0, "marbles"),
            # ADR-0131.G.3 integration: 'dollars'/'cents' surface units normalize to
            # canonical 'cents'. For verb-class coverage we use a non-money unit so
            # the test isolates the 'saved' verb axis from G.3 normalization.
            ("Sam saved 12 marbles. How many marbles does Sam have?", 12.0, "marbles"),
            ("Sam saved up 15 stickers. How many stickers does Sam have?", 15.0, "stickers"),
            ("Sam started 20 pencils. How many pencils does Sam have?", 20.0, "pencils"),
            ("Sam started with 6 toys. How many toys does Sam have?", 6.0, "toys"),
            ("Sam had 9 dolls. How many dolls does Sam have?", 9.0, "dolls"),
            ("Sam makes 4 cookies. How many cookies does Sam have?", 4.0, "cookies")
        ]
        for problem, expected_val, expected_unit in verbs:
            res = parse_and_solve(problem)
            assert res.is_admitted, f"Failed to admit verb problem: {problem}"
            assert res.answer == expected_val
            assert res.selected_graph is not None
            assert res.selected_graph.unknown.unit == expected_unit


class TestG1AdversarialProbes:
    def test_makes_rate_is_refused(self) -> None:
        # 'makes' in rate context ("Tina makes $18.00 an hour") must be refused
        problem = "Tina makes $18.00 an hour. How many dollars does Tina have?"
        res = parse_and_solve(problem)
        assert not res.is_admitted

    def test_subjunctive_had_is_refused(self) -> None:
        # "If Sam had 5 apples" is hypothetical, must refuse
        problem = "If Sam had 5 apples, how many would he have?"
        res = parse_and_solve(problem)
        assert not res.is_admitted


class TestG1ReplayDeterminism:
    def test_report_is_deterministic(self, cases) -> None:
        r1 = build_report(cases)
        r2 = build_report(cases)
        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
