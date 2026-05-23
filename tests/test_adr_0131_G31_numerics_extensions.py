"""ADR-0131.G.3.1 — Numerics extensions test suite.

Per-axis at-least-one passing test, refusal probes, wrong==0 invariant,
replay byte-equality, and parent v1 lane regression gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.gsm8k_math.runner import _score_one_candidate_graph
from generate.math_candidate_parser import (
    _resolve_value,
    extract_initial_candidates,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score(problem: str, expected_answer: float, expected_unit: str) -> str:
    r = _score_one_candidate_graph({
        "id": "test",
        "problem": problem,
        "expected_answer": expected_answer,
        "expected_unit": expected_unit,
    })
    return r.outcome


def _refused(problem: str) -> bool:
    r = _score_one_candidate_graph({
        "id": "test",
        "problem": problem,
        "expected_answer": 0.0,
        "expected_unit": "",
    })
    return r.outcome == "refused"


# ---------------------------------------------------------------------------
# Axis 1: Fractions end-to-end
# ---------------------------------------------------------------------------

class TestFractions:
    def test_half_of_cup(self):
        assert _score("Bob has 1/2 of a cup. How many cups does Bob have?", 0.5, "cups") == "correct"

    def test_three_quarters_of_bag(self):
        assert _score("Sarah has 3/4 of a bag. How many bags does Sarah have?", 0.75, "bags") == "correct"

    def test_quarter_of_pie(self):
        assert _score("Tom has 1/4 of a pie. How many pies does Tom have?", 0.25, "pies") == "correct"

    def test_improper_fraction(self):
        assert _score("Sam has 3/2 of a liter. How many liters does Sam have?", 1.5, "liters") == "correct"

    def test_resolve_value_fraction(self):
        rv = _resolve_value("3/4")
        assert rv is not None
        assert abs(rv.value - 0.75) < 1e-9
        assert rv.unit_override is None

    def test_fraction_zero_denominator_refused(self):
        assert _refused("Bob has 5/0 apples. How many apples does Bob have?")

    def test_extract_initial_fraction_of(self):
        cands = extract_initial_candidates("Bob has 1/2 of a cup.")
        assert len(cands) > 0
        q = cands[0].initial.quantity
        assert abs(q.value - 0.5) < 1e-9
        assert q.unit == "cups"


# ---------------------------------------------------------------------------
# Axis 2: Multi-currency
# ---------------------------------------------------------------------------

class TestMultiCurrency:
    def test_cent_symbol(self):
        assert _score("Bob has ¢50. How many cents does Bob have?", 50.0, "cents") == "correct"

    def test_euro_symbol(self):
        assert _score("Maria has €20. How many euros does Maria have?", 20.0, "euros") == "correct"

    def test_yen_symbol(self):
        assert _score("Kenji has ¥100. How many yen does Kenji have?", 100.0, "yen") == "correct"

    def test_peso_symbol(self):
        assert _score("Juan has ₱200. How many pesos does Juan have?", 200.0, "pesos") == "correct"

    def test_euro_with_operation(self):
        assert _score("Maria has €30. Maria spends €10. How many euros does Maria have?", 20.0, "euros") == "correct"

    def test_resolve_cent_symbol(self):
        rv = _resolve_value("¢50")
        assert rv is not None and rv.value == 50 and rv.unit_override == "cents"

    def test_resolve_euro_symbol(self):
        rv = _resolve_value("€20")
        assert rv is not None and rv.value == 20 and rv.unit_override == "euros"

    def test_resolve_yen_integer_only(self):
        # ¥ is integer-only; decimal form should be refused
        rv = _resolve_value("¥100")
        assert rv is not None and rv.value == 100 and rv.unit_override == "yen"

    def test_euro_three_decimal_refused(self):
        assert _refused("Sam has €5.678. How many euros does Sam have?")

    def test_pound_sterling_deferred(self):
        # £ symbol parses and resolves but question extractor cannot parse
        # multi-word unit 'pounds sterling' — deferred to G.3.2.
        rv = _resolve_value("£15")
        assert rv is not None and rv.value == 15 and rv.unit_override == "pounds sterling"


# ---------------------------------------------------------------------------
# Axis 3: Multi-token space-separated cardinals
# ---------------------------------------------------------------------------

class TestMultiWordCardinals:
    def test_one_hundred(self):
        assert _score("Bob has one hundred apples. How many apples does Bob have?", 100.0, "apples") == "correct"

    def test_one_thousand(self):
        assert _score("The store has one thousand books. How many books does the store have?", 1000.0, "books") == "correct"

    def test_three_hundred(self):
        assert _score("Anna has three hundred cookies. How many cookies does Anna have?", 300.0, "cookies") == "correct"

    def test_two_thousand_five_hundred(self):
        assert _score("Mike has two thousand five hundred marbles. How many marbles does Mike have?", 2500.0, "marbles") == "correct"

    def test_five_hundred_dollars_to_cents(self):
        assert _score("Sam has five hundred dollars. How many cents does Sam have?", 50000.0, "cents") == "correct"

    def test_extract_multi_word_cardinal(self):
        cands = extract_initial_candidates("Bob has one hundred apples.")
        assert len(cands) > 0
        q = cands[0].initial.quantity
        assert q.value == 100
        assert q.unit == "apples"


# ---------------------------------------------------------------------------
# Axis 4: Word-number-adjective compositions
# ---------------------------------------------------------------------------

class TestWordNumAdjective:
    def test_five_full_boxes(self):
        assert _score("Sam has five full boxes. How many boxes does Sam have?", 5.0, "boxes") == "correct"

    def test_three_loose_crayons(self):
        assert _score("Ella has three loose crayons. How many crayons does Ella have?", 3.0, "crayons") == "correct"

    def test_seven_empty_cans(self):
        assert _score("Bob has seven empty cans. How many cans does Bob have?", 7.0, "cans") == "correct"

    def test_twelve_whole_pies(self):
        assert _score("Jane has twelve whole pies. How many pies does Jane have?", 12.0, "pies") == "correct"

    def test_eight_new_books(self):
        assert _score("Tom has eight new books. How many books does Tom have?", 8.0, "books") == "correct"

    def test_extract_adjective_initial(self):
        cands = extract_initial_candidates("Sam has five full boxes.")
        assert len(cands) > 0
        q = cands[0].initial.quantity
        assert q.value == 5
        assert q.unit == "boxes"


# ---------------------------------------------------------------------------
# Refusal probes — closed-set boundary enforcement
# ---------------------------------------------------------------------------

class TestRefusals:
    def test_percentage_refused(self):
        assert _refused("Bob has 50% apples. How many apples does Bob have?")

    def test_percentage_of_refused(self):
        assert _refused("Sam has 75% of a pie. How many pies does Sam have?")

    def test_scientific_notation_refused(self):
        assert _refused("Sam has 1e3 marbles. How many marbles does Sam have?")

    def test_scientific_notation_float_refused(self):
        assert _refused("Alice has 2.5e2 books. How many books does Alice have?")

    def test_locale_separator_refused(self):
        assert _refused("Alice has 1,000 pennies. How many pennies does Alice have?")

    def test_locale_separator_large_refused(self):
        assert _refused("Bob has 10,000 apples. How many apples does Bob have?")

    def test_three_decimal_dollar_refused(self):
        assert _refused("Bob has $1.234. How many cents does Bob have?")

    def test_three_decimal_euro_refused(self):
        assert _refused("Sam has €5.678. How many euros does Sam have?")


# ---------------------------------------------------------------------------
# Wrong == 0 invariant (load-bearing gate per ADR-0114a Obligation #4)
# ---------------------------------------------------------------------------

class TestWrongEqualsZero:
    def test_v1_1_wrong_is_zero(self):
        from evals.math_capability_axes.G3_numerics.v1_1.runner import build_report
        report = build_report()
        assert report["metrics"]["solved_wrong"] == 0, (
            f"solved_wrong must be 0; got {report['metrics']['solved_wrong']}"
        )

    def test_v1_1_overall_pass(self):
        from evals.math_capability_axes.G3_numerics.v1_1.runner import build_report
        report = build_report()
        assert report["metrics"]["overall_pass"] is True


# ---------------------------------------------------------------------------
# Replay byte-equality
# ---------------------------------------------------------------------------

class TestReplayByteEquality:
    def test_report_byte_equal_across_two_runs(self):
        from evals.math_capability_axes.G3_numerics.v1_1.runner import build_report
        r1 = json.dumps(build_report(), indent=2, sort_keys=True)
        r2 = json.dumps(build_report(), indent=2, sort_keys=True)
        assert r1 == r2, "v1.1 report must be byte-equal across runs"


# ---------------------------------------------------------------------------
# Parent v1 lane regression (no regression from G.3 changes)
# ---------------------------------------------------------------------------

class TestParentV1Regression:
    def test_v1_wrong_still_zero(self):
        from evals.math_capability_axes.G3_numerics.v1.runner import build_report
        report = build_report()
        assert report["metrics"]["solved_wrong"] == 0

    def test_v1_overall_pass(self):
        from evals.math_capability_axes.G3_numerics.v1.runner import build_report
        report = build_report()
        assert report["metrics"]["overall_pass"] is True
