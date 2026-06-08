"""Tests for the R3 single-rate reader (R3d).

Pins wrong=0: every well-formed fixture reads to exactly the gold setup; every reader_refuses
fixture refuses with its gold reason; and — end to end — every solved fixture reads → solves →
ties to its labeled answer (reusing R2's answer-choice verifier). Plus the unit-mismatch gate.
"""

from __future__ import annotations

from evals.rate_oracle.runner import _load_rate_gold, gold_to_problem, run_reader
from evals.rate_oracle.signature import rate_setup_signature
from generate.answer_choices.verify import ChoiceVerdict, verify_answer_choice
from generate.meaning_graph.reader import Refusal
from generate.rate_comprehension.reader import read_rate_problem
from generate.rate_comprehension.solver import solve_rate


def _by(expect: str) -> list[dict]:
    return [f for f in _load_rate_gold() if f["expect"] == expect]


def test_reader_lane_is_wrong_zero_and_complete() -> None:
    r = run_reader()
    assert r["setup_wrong"] == 0 and r["reason_mismatch"] == 0
    assert r["setup_refused"] == 0
    assert r["setup_correct"] == 9  # 7 solved (incl. the convertible r3-09) + 2 solver_refuses
    assert r["refused_correct"] == 4


def test_reads_every_well_formed_fixture_to_gold_signature() -> None:
    for fx in _by("solved") + _by("solver_refuses"):
        out = read_rate_problem(fx["text"])
        assert not isinstance(out, Refusal), f"{fx['id']}: {getattr(out, 'reason', '')}"
        assert rate_setup_signature(out) == rate_setup_signature(gold_to_problem(fx)), fx["id"]


def test_refuses_every_reader_refuse_fixture_with_reason() -> None:
    for fx in _by("reader_refuses"):
        out = read_rate_problem(fx["text"])
        assert isinstance(out, Refusal) and out.reason == fx["reader_reason"], fx["id"]


def test_read_solve_verify_end_to_end_for_solved() -> None:
    for fx in _by("solved"):
        problem = read_rate_problem(fx["text"])
        assert not isinstance(problem, Refusal), fx["id"]
        value = solve_rate(problem)
        assert value == fx["gold"], fx["id"]
        verdict = verify_answer_choice(value, fx["options"], fx["answer"])
        assert isinstance(verdict, ChoiceVerdict) and verdict.status == "consistent"
        assert verdict.computed_label == fx["answer"]


def test_read_then_solver_refuses_for_solver_refuse_fixtures() -> None:
    for fx in _by("solver_refuses"):
        problem = read_rate_problem(fx["text"])
        assert not isinstance(problem, Refusal), fx["id"]
        out = solve_rate(problem)
        assert isinstance(out, Refusal) and out.reason == fx["solver_reason"], fx["id"]


def test_constructed_unit_mismatch_refuses() -> None:
    # rate per hour, duration in days — does not compose -> refuse (never converts).
    out = read_rate_problem("A car travels 70 miles per hour for 2 days. How many miles does it travel?")
    assert isinstance(out, Refusal) and out.reason == "rate_unit_mismatch"
