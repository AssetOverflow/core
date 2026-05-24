"""ADR-0131.G.5 — Aggregate answer composition axis lane tests.

Pins the closed aggregate-cue vocabulary (``in total``, ``altogether``,
``combined``, ``together``) and the end-to-end ``parse_and_solve`` path
for 2-entity, 3-entity, single-entity, and refusal shapes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.math_capability_axes.G5_aggregate.v1.runner import build_report
from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import extract_question_candidates

_REPO = Path(__file__).resolve().parent.parent
_GSM8K_LEGACY_REPORT = (
    _REPO / "evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json"
)
_GSM8K_CG_REPORT = _REPO / "evals/gsm8k_math/train_sample/v1/report.json"


# ── Cue vocabulary tests ─────────────────────────────────────────────


class TestCueVocabulary:
    """Verify that combined and together parse to entity=None."""

    @pytest.mark.parametrize("cue", ["combined", "together", "altogether", "in total"])
    def test_cue_parses_to_entity_none(self, cue: str) -> None:
        q = f"How many apples do they have {cue}?"
        cands = extract_question_candidates(q)
        assert len(cands) >= 1, f"no candidate for cue {cue!r}"
        assert cands[0].unknown.entity is None
        assert cands[0].unknown.unit == "apples"

    def test_closed_cue_docstring_lists_all_four(self) -> None:
        import generate.math_candidate_parser as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        for cue in ("in total", "altogether", "combined", "together"):
            assert cue in src, f"cue {cue!r} missing from parser source"


# ── End-to-end parse_and_solve tests ─────────────────────────────────


class TestTwoEntityNoOp:
    @pytest.mark.parametrize(
        "problem, expected",
        [
            ("Sam has 5 apples. Tom has 3 apples. How many apples do they have altogether?", 8.0),
            ("Alice has 7 books. Bob has 4 books. How many books do they have in total?", 11.0),
            ("Maya has 6 coins. Leo has 9 coins. How many coins do they have combined?", 15.0),
            ("Jade has 12 stickers. Finn has 8 stickers. How many stickers do they have together?", 20.0),
        ],
    )
    def test_two_entity_sum(self, problem: str, expected: float) -> None:
        r = parse_and_solve(problem)
        assert r.answer == expected
        assert r.refusal_reason is None


class TestThreeEntityNoOp:
    @pytest.mark.parametrize(
        "problem, expected",
        [
            ("Sam has 5 apples. Tom has 3 apples. Amy has 2 apples. How many apples do they have altogether?", 10.0),
            ("Alice has 4 books. Bob has 6 books. Carol has 2 books. How many books do they have in total?", 12.0),
            ("Maya has 10 coins. Leo has 5 coins. Nina has 3 coins. How many coins do they have combined?", 18.0),
            ("Jade has 7 stickers. Finn has 4 stickers. Rex has 9 stickers. How many stickers do they have together?", 20.0),
        ],
    )
    def test_three_entity_sum(self, problem: str, expected: float) -> None:
        r = parse_and_solve(problem)
        assert r.answer == expected
        assert r.refusal_reason is None


class TestSingleEntityDegenerate:
    def test_single_entity_identity(self) -> None:
        r = parse_and_solve("Sam has 5 apples. How many apples do they have in total?")
        assert r.answer == 5.0

    def test_single_entity_with_op(self) -> None:
        r = parse_and_solve("Alice has 7 books. Alice buys 3 books. How many books do they have altogether?")
        assert r.answer == 10.0


class TestMismatchedUnitRefusal:
    @pytest.mark.parametrize(
        "problem",
        [
            "Sam has 5 apples. Tom has 3 apples. How many apples does everyone have?",
            "Alice has 4 coins. Bob has 6 coins. What is the total number of coins?",
            "Maya has 10 books. Leo has 5 books. How many books do Sam and Leo have?",
            "Jade has 8 stickers. Finn has 4 stickers. How many stickers are there?",
        ],
    )
    def test_outside_closed_cue_refuses(self, problem: str) -> None:
        r = parse_and_solve(problem)
        assert r.answer is None, f"expected refusal but got {r.answer}"


# ── Axis lane gate ───────────────────────────────────────────────────


class TestAxisLaneGate:
    def test_wrong_is_zero(self) -> None:
        report = build_report()
        assert report["metrics"]["wrong"] == 0
        assert report["metrics"]["wrong_count_is_zero"] is True

    def test_report_byte_equal_across_runs(self) -> None:
        r1 = build_report()
        r2 = build_report()
        s1 = json.dumps(r1, indent=2, sort_keys=True)
        s2 = json.dumps(r2, indent=2, sort_keys=True)
        assert s1 == s2

    def test_all_categories_present(self) -> None:
        report = build_report()
        expected_cats = {
            "2entity_no_op",
            "3entity_no_op",
            "2entity_with_op",
            "single_entity_total_cue",
            "refusal_outside_closed_cue",
        }
        assert set(report["per_category"].keys()) == expected_cats


# ── B3 regression guard ──────────────────────────────────────────────


def test_b3_lane_still_passes() -> None:
    """B3 bounded-grammar lane must remain green after G5 changes."""
    from evals.math_bounded_grammar.v1.runner import build_report as b3_build, load_cases

    cases_path = _REPO / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
    report = b3_build(load_cases(cases_path))
    assert report["metrics"]["wrong"] == 0, (
        f"B3 lane regression: wrong={report['metrics']['wrong']}"
    )


# ── GSM8K safety rail ────────────────────────────────────────────────


def test_gsm8k_legacy_probe_safety_rail_intact() -> None:
    """ADR-0131.G invariant: legacy probe still shows admitted_wrong == 0."""
    data = json.loads(_GSM8K_LEGACY_REPORT.read_text(encoding="utf-8"))
    assert data["metrics"]["admitted_wrong"] == 0


def test_gsm8k_candidate_graph_probe_wrong_zero() -> None:
    """ADR-0131.G invariant: candidate-graph probe shows wrong == 0."""
    data = json.loads(_GSM8K_CG_REPORT.read_text(encoding="utf-8"))
    assert data["counts"]["wrong"] == 0
