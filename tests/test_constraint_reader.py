"""Tests for the R2 two-category reader (C5–C9).

Pins the wrong=0 reader contract: every well-formed fixture reads to EXACTLY the gold setup
signature, every ``reader_refuses`` fixture refuses with its gold reason, and — proving each
reader slice end to end — every solved fixture reads -> solves -> ties to its labeled answer.
The defensive guards (coefficient unit mismatch, off-category query) are exercised by
construction; the too-many-categories guard is shown meaningful-fail against a 2-category twin.
"""

from __future__ import annotations

from evals.constraint_oracle.runner import _load_r2_gold, gold_to_problem, run_reader
from evals.constraint_oracle.signature import constraint_setup_signature
from generate.answer_choices.verify import ChoiceVerdict, verify_answer_choice
from generate.constraint_comprehension.reader import read_constraint_problem
from generate.constraint_comprehension.solver import answer_constraint_problem
from generate.meaning_graph.reader import Refusal


def _by_expect(expect: str) -> list[dict]:
    return [f for f in _load_r2_gold() if f["expect"] == expect]


def test_reader_lane_is_wrong_zero_and_complete() -> None:
    r = run_reader()
    assert r["setup_wrong"] == 0
    assert r["reason_mismatch"] == 0
    assert r["setup_refused"] == 0  # every well-formed fixture reads at C9
    assert r["setup_correct"] == 10  # 7 solved + 3 solver_refuses (all have valid setups)
    assert r["refused_correct"] == 3  # the three reader_refuses fixtures


def test_reader_reads_every_well_formed_fixture_to_gold_signature() -> None:
    for fx in _by_expect("solved") + _by_expect("solver_refuses"):
        out = read_constraint_problem(fx["text"])
        assert not isinstance(out, Refusal), f"{fx['id']} refused: {getattr(out, 'reason', '')}"
        assert constraint_setup_signature(out) == constraint_setup_signature(gold_to_problem(fx)), fx["id"]


def test_reader_refuses_every_reader_refuse_fixture_with_its_reason() -> None:
    for fx in _by_expect("reader_refuses"):
        out = read_constraint_problem(fx["text"])
        assert isinstance(out, Refusal), fx["id"]
        assert out.reason == fx["reader_reason"], f"{fx['id']}: {out.reason} != {fx['reader_reason']}"


def test_read_solve_verify_end_to_end_for_solved() -> None:
    # The full chain a reader slice must prove: read -> solve -> tie to the labeled option.
    for fx in _by_expect("solved"):
        problem = read_constraint_problem(fx["text"])
        assert not isinstance(problem, Refusal), fx["id"]
        value = answer_constraint_problem(problem)
        assert value == fx["gold"], fx["id"]
        verdict = verify_answer_choice(value, fx["options"], fx["answer"], noun=problem.query.unit)
        assert isinstance(verdict, ChoiceVerdict) and verdict.status == "consistent"
        assert verdict.computed_label == fx["answer"]


def test_read_then_solver_refuses_for_solver_refuse_fixtures() -> None:
    # The reader reads the setup; the SOLVER owns solvability — read correct, solve refuses.
    for fx in _by_expect("solver_refuses"):
        problem = read_constraint_problem(fx["text"])
        assert not isinstance(problem, Refusal), fx["id"]
        out = answer_constraint_problem(problem)
        assert isinstance(out, Refusal) and out.reason == fx["solver_reason"], fx["id"]


# --- defensive guards (no gold fixture; exercised by construction) --------------------- #


def test_coefficient_unit_mismatch_refuses() -> None:
    out = read_constraint_problem(
        "A shop has 5 things, all cars and trucks. Each car has 4 wheels and each truck costs "
        "3 dollars. The things total 20 wheels. How many cars are there?"
    )
    assert isinstance(out, Refusal) and out.reason == "coefficient_unit_mismatch"


def test_weighted_total_in_wrong_unit_refuses() -> None:
    # Hazard: the weighted total's unit must match the coefficient unit. Coefficients are in
    # students; a total in DOLLARS matches no coefficient unit, so the weighted equation is
    # never assembled -> missing_weighted_total. The reader never sums across units.
    out = read_constraint_problem(
        "A school rents 6 buses. Each large bus holds 50 students and each small bus holds "
        "30 students. The buses cost 260 dollars in total. How many large buses are there?"
    )
    assert isinstance(out, Refusal) and out.reason == "missing_weighted_total"


def test_off_category_query_refuses() -> None:
    out = read_constraint_problem(
        "A school rents 6 buses for a trip. Each large bus holds 50 students and each small bus "
        "holds 30 students. The buses carry 260 students in total. How many vans are there?"
    )
    assert isinstance(out, Refusal) and out.reason == "query_target_not_a_category"


def test_too_many_categories_is_meaningful_fail_against_two_category_twin() -> None:
    # The 3-category text refuses; the SAME template with exactly two categories reads.
    three = read_constraint_problem(
        "A lot has 10 vehicles. Each car has 4 wheels, each motorcycle has 2 wheels, and each "
        "truck has 6 wheels. Together the vehicles have 34 wheels. How many cars are there?"
    )
    assert isinstance(three, Refusal) and three.reason == "too_many_categories"
    two = read_constraint_problem(
        "A lot has 10 vehicles. Each car has 4 wheels and each motorcycle has 2 wheels. "
        "Together the vehicles have 32 wheels. How many cars are there?"
    )
    assert not isinstance(two, Refusal)
    assert {u.symbol for u in two.unknowns} == {"car", "motorcycle"}
