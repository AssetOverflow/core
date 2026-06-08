"""Tests for the combined-rate prose reader (CMB-c).

Pins wrong=0 for the reader: every well-formed gold fixture reads to exactly the gold setup (and
solves end-to-end to its labeled answer via CMB-b); every reader_refuses fixture refuses with its
gold reason; the CMB-a 2x2 domain-entry grid (with fresh vocabulary, proving the reader is
structural not string-matched); the solver-boundary fixtures are PARSED then refused by the solver,
not the reader; and router-organ hygiene — CMB steps aside on every foreign R1/R2/R3 problem.
"""

from __future__ import annotations

from pathlib import Path

from evals.combined_rate_oracle.runner import _load_combined_rate_gold, gold_to_problem, run_reader
from evals.combined_rate_oracle.signature import combined_rate_setup_signature
from evals.constraint_oracle.runner import _load_r2_gold
from evals.rate_oracle.runner import _load_rate_gold
from evals.setup_oracle.runner import _load_r1_gold
from generate.answer_choices.verify import ChoiceVerdict, verify_answer_choice
from generate.combined_rate_comprehension.model import CombinedRateProblem
from generate.combined_rate_comprehension.reader import read_combined_rate_problem
from generate.combined_rate_comprehension.solver import solve_combined_rate
from generate.meaning_graph.reader import Refusal

_PAGE_HOUR = ("page", "hour")


def _by(expect: str) -> list[dict]:
    return [f for f in _load_combined_rate_gold() if f["expect"] == expect]


# --- the reader lane + gold round-trip ---------------------------------------------------- #


def test_reader_lane_is_wrong_zero_and_complete() -> None:
    r = run_reader()
    assert r["setup_wrong"] == 0 and r["reason_mismatch"] == 0
    assert r["setup_refused"] == 0
    assert r["setup_correct"] == 11  # 6 solved + 5 solver_refuses (all parse)
    assert r["refused_correct"] == 7


def test_reads_every_well_formed_fixture_to_gold_signature() -> None:
    for fx in _by("solved") + _by("solver_refuses"):
        out = read_combined_rate_problem(fx["text"])
        assert not isinstance(out, Refusal), f"{fx['id']}: refused {getattr(out, 'reason', '')}"
        assert combined_rate_setup_signature(out) == combined_rate_setup_signature(gold_to_problem(fx)), fx["id"]


def test_refuses_every_reader_refuse_fixture_with_reason() -> None:
    for fx in _by("reader_refuses"):
        out = read_combined_rate_problem(fx["text"])
        assert isinstance(out, Refusal) and out.reason == fx["reader_reason"], fx["id"]


def test_read_solve_verify_end_to_end_for_solved() -> None:
    for fx in _by("solved"):
        problem = read_combined_rate_problem(fx["text"])
        assert not isinstance(problem, Refusal), fx["id"]
        value = solve_combined_rate(problem)
        assert value == fx["gold"], fx["id"]
        verdict = verify_answer_choice(value, fx["options"], fx["answer"])
        assert isinstance(verdict, ChoiceVerdict) and verdict.status == "consistent"
        assert verdict.computed_label == fx["answer"], fx["id"]


def test_solver_boundary_fixtures_are_parsed_by_reader_then_refused_by_solver() -> None:
    # The division of labor: the reader OWNS the setup (non-positive net / non-integer are valid
    # combined-rate setups), the solver OWNS solvability. The reader must NOT refuse these.
    for fx in _by("solver_refuses"):
        problem = read_combined_rate_problem(fx["text"])
        assert not isinstance(problem, Refusal), f"{fx['id']}: reader wrongly refused a solver-boundary case"
        out = solve_combined_rate(problem)
        assert isinstance(out, Refusal) and out.reason == fx["solver_reason"], fx["id"]


# --- the 2x2 domain-entry grid, with FRESH vocabulary (structural, not gold-string-matched) ---- #


def test_grid_two_rates_plus_cooperative_cue_parses_sum() -> None:
    out = read_combined_rate_problem(
        "Carla types 4 pages per hour and Dave types 3 pages per hour. Working together, how many pages in 5 hours?"
    )
    assert isinstance(out, CombinedRateProblem)
    assert out.combine_mode == "sum" and out.query == "quantity"
    assert solve_combined_rate(out) == 35  # (4 + 3) * 5


def test_grid_two_rates_plus_opposing_cue_parses_difference() -> None:
    out = read_combined_rate_problem(
        "A tap adds 7 liters per minute while a leak removes 2 liters per minute. How many liters after 4 minutes?"
    )
    assert isinstance(out, CombinedRateProblem)
    assert out.combine_mode == "difference" and out.query == "quantity"
    assert solve_combined_rate(out) == 20  # (7 - 2) * 4


def test_grid_two_rates_no_cue_is_combine_mode_ambiguous() -> None:
    out = read_combined_rate_problem(
        "Machine X makes 4 bolts per minute. Machine Y makes 6 bolts per minute. How many bolts in 3 minutes?"
    )
    assert isinstance(out, Refusal) and out.reason == "combine_mode_ambiguous"


def test_grid_one_rate_plus_cue_is_missing_second_rate() -> None:
    out = read_combined_rate_problem(
        "Sam and Tess mow a lawn together. Sam mows 2 lawns per hour. How many lawns in 3 hours?"
    )
    assert isinstance(out, Refusal) and out.reason == "missing_second_rate"


def test_grid_one_rate_no_cue_steps_aside() -> None:
    out = read_combined_rate_problem("A printer prints 5 pages per minute for 4 minutes. How many pages does it print?")
    assert isinstance(out, Refusal) and out.reason == "not_combined_rate_shaped"


# --- each remaining reader refusal reason, meaningful-fail (fresh text) -------------------- #


def test_rate_unit_mismatch() -> None:
    out = read_combined_rate_problem(
        "A clerk files 3 forms per hour and a pump moves 2 gallons per minute. Working together, how much in 4 hours?"
    )
    assert isinstance(out, Refusal) and out.reason == "rate_unit_mismatch"


def test_three_or_more_rates() -> None:
    out = read_combined_rate_problem(
        "A types 3 pages per hour, B types 2 pages per hour, and C types 5 pages per hour. Together, how many pages in 2 hours?"
    )
    assert isinstance(out, Refusal) and out.reason == "three_or_more_rates"


def test_reciprocal_work_rate_deferred() -> None:
    out = read_combined_rate_problem(
        "Maria can paint a fence in 4 hours, and Nina can paint the same fence in 6 hours. Working together, how many hours?"
    )
    assert isinstance(out, Refusal) and out.reason == "reciprocal_work_rate_deferred"


def test_clock_interval_deferred() -> None:
    out = read_combined_rate_problem(
        "One hose fills at 3 liters per minute and another fills at 2 liters per minute, together from 1 pm to 4 pm. How many liters?"
    )
    assert isinstance(out, Refusal) and out.reason == "clock_interval_deferred"


def test_sequential_segments_step_aside_not_ambiguous() -> None:
    # Two rate clauses, each with its OWN duration -> sequential (R3.x), NOT a combination. Must
    # step aside, never claim the substantive combine_mode_ambiguous (hygiene).
    out = read_combined_rate_problem(
        "A car goes 60 miles per hour for 2 hours and then 40 miles per hour for 3 hours. How many miles total?"
    )
    assert isinstance(out, Refusal) and out.reason == "not_combined_rate_shaped"


# --- router-organ hygiene: CMB steps aside on every foreign R1/R2/R3 problem --------------- #


def test_steps_aside_on_all_foreign_r1_r2_r3_gold() -> None:
    # The ONLY refusal reason CMB may use on foreign text is the input_shape-family
    # not_combined_rate_shaped — never a substantive boundary (router-organ-hygiene invariant).
    for load in (_load_r1_gold, _load_r2_gold, _load_rate_gold):
        for fx in load():
            out = read_combined_rate_problem(fx["text"])
            assert isinstance(out, Refusal), f"{fx['id']}: CMB produced a setup on foreign text"
            assert out.reason == "not_combined_rate_shaped", f"{fx['id']}: substantive reason {out.reason!r} on foreign text"


def test_does_not_steal_ordinary_single_rate_problems() -> None:
    # Plain R3 single-rate prose (incl. the clock/temporal r3 case) is R3's; CMB must step aside.
    for text in (
        "A car travels 60 miles per hour for 3 hours. How many miles does it travel?",
        "A worker earns 15 dollars per hour for 8 hours. How many dollars does she earn?",
        "A machine makes 12 widgets per minute. It runs for 5 minutes. How many widgets does it make?",
    ):
        out = read_combined_rate_problem(text)
        assert isinstance(out, Refusal) and out.reason == "not_combined_rate_shaped", text


# --- regression tests for the adversarial-found defects (wrong=0 / hygiene) --------------- #


def test_difference_mode_is_role_based_not_positional() -> None:
    # Drain listed FIRST must still subtract: 3 (fill) - 8 (drain) = -5 -> solver refuses, NOT a
    # positive answer of (8-3)*5. Both orders must agree on the role assignment.
    drain_first = read_combined_rate_problem(
        "A drain removes 8 liters per minute while a pipe fills a tank at 3 liters per minute. How many liters after 5 minutes?"
    )
    assert isinstance(drain_first, CombinedRateProblem)
    assert drain_first.combine_mode == "difference" and drain_first.effective_rate == -5
    assert isinstance(solve_combined_rate(drain_first), Refusal)
    fill_first = read_combined_rate_problem(
        "A pump fills a tank at 9 liters per minute while a drain removes 3 liters per minute. How many liters after 5 minutes?"
    )
    assert isinstance(fill_first, CombinedRateProblem) and solve_combined_rate(fill_first) == 30


def test_lone_drain_word_is_cooperative_not_opposing() -> None:
    # "drain the backlog" is a verb, not opposing flow; with no fill counterpart it is a cooperative
    # (sum) problem, not difference.
    out = read_combined_rate_problem(
        "Both workers drain the backlog at 5 tasks per hour and 3 tasks per hour. How many tasks in 4 hours?"
    )
    assert isinstance(out, CombinedRateProblem) and out.combine_mode == "sum"
    assert solve_combined_rate(out) == 32


def test_mid_sentence_combined_rate_does_not_steal_quantity_query() -> None:
    out = read_combined_rate_problem(
        "Machine A fills 6 tanks per hour and Machine B fills 4 tanks per hour. At their combined rate, how many tanks in 5 hours?"
    )
    assert isinstance(out, CombinedRateProblem) and out.query == "quantity"
    assert solve_combined_rate(out) == 50


def test_preamble_number_is_not_the_query_target() -> None:
    # The "in 3 hours / 15 rooms" preamble must not be read as the query duration/quantity.
    out = read_combined_rate_problem(
        "In 3 hours, Anna and Ben painted 15 rooms. Anna paints 3 rooms per hour and Ben paints 2 rooms per hour. "
        "Working together, how many rooms do they paint in 4 hours?"
    )
    assert isinstance(out, CombinedRateProblem) and out.time == 4
    assert solve_combined_rate(out) == 20


def test_decimal_rates_step_aside() -> None:
    out = read_combined_rate_problem(
        "Carla types 3.5 pages per hour and Dave types 2.5 pages per hour. Working together, how many pages in 4 hours?"
    )
    assert isinstance(out, Refusal) and out.reason == "not_combined_rate_shaped"


def test_incidental_combination_words_step_aside() -> None:
    # 'combined'/'both'/'together' used as non-combination words on single-rate text must NOT
    # over-claim missing_second_rate (hygiene) — step aside.
    for text in (
        "Anna earns 3 dollars per hour. If they work together, how many dollars does Anna earn in 4 hours?",
        "A machine produces 5 parts per hour. The combined output target is 25 parts. How many hours does it take?",
        "A study entitled Combined Effects found workers process 4 tasks per hour. How many tasks in 8 hours?",
    ):
        out = read_combined_rate_problem(text)
        assert isinstance(out, Refusal) and out.reason == "not_combined_rate_shaped", text


def test_foreign_multi_rate_text_steps_aside_not_substantive() -> None:
    # Substantive refusals (rate_unit_mismatch / three_or_more_rates) must NOT fire on foreign prose
    # that merely contains 2+ rate patterns with no combination cue (router-organ hygiene).
    for text in (
        "The server handles 100 requests per second and costs 2 dollars per hour. How many requests in 10 seconds?",
        "A types 3 pages per hour, B types 2 pages per hour, and C types 5 pages per hour. How many pages in 2 hours?",
    ):
        out = read_combined_rate_problem(text)
        assert isinstance(out, Refusal) and out.reason == "not_combined_rate_shaped", text


def test_duration_unit_mismatch_refuses() -> None:
    # A combined problem whose duration unit differs from the rate denominator: CMB v1 does not
    # convert (that is R3.2, single-rate only) -> rate_unit_mismatch. Pins the line-144 exit.
    out = read_combined_rate_problem(
        "Pipe A fills 5 rooms per hour and Pipe B fills 3 rooms per hour. Working together, how many rooms in 30 minutes?"
    )
    assert isinstance(out, Refusal) and out.reason == "rate_unit_mismatch"


# --- second-pass regression: incidental cues, distractor numbers, loose sequential ------- #


def test_incidental_drain_noun_does_not_force_difference() -> None:
    # "the drain stays closed" / "drain from the tank" are not drain RATES — two fills cooperating
    # must stay sum, never flip to difference.
    a = read_combined_rate_problem(
        "The pump fills 8 liters per minute and the hose fills 4 liters per minute together. The drain stays closed. How many liters in 3 minutes?"
    )
    assert isinstance(a, CombinedRateProblem) and a.combine_mode == "sum" and solve_combined_rate(a) == 36
    b = read_combined_rate_problem(
        "Pump A fills 10 liters per minute and pump B fills 6 liters per minute together. How many liters drain from the tank in 2 minutes?"
    )
    assert isinstance(b, CombinedRateProblem) and b.combine_mode == "sum" and solve_combined_rate(b) == 32


def test_unresolvable_drain_role_steps_aside_not_wrong_answer() -> None:
    # A drain verb that does not cleanly govern one rate clause -> no clean opposition -> refuse
    # (safe), never emit a positive answer with an inverted role.
    out = read_combined_rate_problem(
        "Pipe A pumps 10 gallons per minute, draining the reservoir, and Pipe B fills 3 gallons per minute. How many gallons in 2 minutes?"
    )
    assert isinstance(out, Refusal) and out.reason == "combine_mode_ambiguous"


def test_time_query_quantity_ignores_preamble_distractor() -> None:
    out = read_combined_rate_problem(
        "Pump A adds 6 liters per minute and pump B adds 4 liters per minute together. "
        "There are already 50 liters in the tank. How many minutes to fill 100 liters?"
    )
    assert isinstance(out, CombinedRateProblem) and out.quantity == 100 and solve_combined_rate(out) == 10


def test_quantity_query_duration_ignores_transitional_distractor() -> None:
    out = read_combined_rate_problem(
        "Pipe A fills 10 liters per minute and pipe B fills 6 liters per minute together. "
        "After 2 minutes and 3 seconds, how many liters are added in 4 minutes?"
    )
    assert isinstance(out, CombinedRateProblem) and out.time == 4 and solve_combined_rate(out) == 64


def test_sequential_segments_with_loose_connector_step_aside() -> None:
    out = read_combined_rate_problem(
        "Machine A produces 10 units per hour, also for 3 hours, and machine B produces 5 units per hour, "
        "also for 2 hours. Both machines work together. How many units total?"
    )
    assert isinstance(out, Refusal) and out.reason == "not_combined_rate_shaped"


def test_compared_rates_with_no_combined_query_step_aside() -> None:
    # Two same-unit rates that are COMPARED, not combined ("which is faster?" / "what is the
    # difference?"), are not a CMB problem -> step aside, never the substantive combine_mode_ambiguous.
    for text in (
        "A car drives 60 miles per hour. A train drives 80 miles per hour. Which is faster?",
        "A printer does 5 pages per minute. A scanner does 3 pages per minute. What is the difference?",
    ):
        out = read_combined_rate_problem(text)
        assert isinstance(out, Refusal) and out.reason == "not_combined_rate_shaped", text


def test_reader_module_is_off_serving() -> None:
    import ast

    import generate.combined_rate_comprehension.reader as reader_mod

    forbidden = ("generate.derivation", "core.reliability_gate")
    for node in ast.walk(ast.parse(Path(str(reader_mod.__file__)).read_text(encoding="utf-8"))):
        names = (
            [a.name for a in node.names] if isinstance(node, ast.Import)
            else [node.module or ""] if isinstance(node, ast.ImportFrom)
            else []
        )
        for name in names:
            assert not any(name.startswith(t) for t in forbidden), f"reader imports {name}"
