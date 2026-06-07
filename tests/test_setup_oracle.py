"""Setup-oracle lane — grade the reading (structure), not the answer.

Two obligations:
1. The current reader reads all 15 relational_metric cases with the gold STRUCTURE
   (``setup_wrong == 0``) — the gate the milestone rests on.
2. The oracle MEANINGFULLY FAILS — a reading that lands on the right number via the
   WRONG structure is ``setup_wrong``. Without this, structure-grading would be
   decoration; with it, "did we read it right?" is falsifiable.
"""

from __future__ import annotations

import pytest

from evals.relational_metric.oracle import OracleError, oracle_answer
from evals.setup_oracle import (
    gold_unknown_signature,
    reader_symbol_units,
    reader_unknown_signature,
    relation_signature,
    run,
    run_r1,
    run_r1_answers,
    symbol_unit_signature,
)
from generate.binding_graph.model import (
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
)


def _span() -> SourceSpanLink:
    return SourceSpanLink(source_id="t", start=0, end=1, text="x")


# --------------------------------------------------------------------------- #
# Obligation 1 — the reader reads the gold structure on every case
# --------------------------------------------------------------------------- #


def test_all_cases_setup_correct_wrong_zero() -> None:
    report = run()
    assert report["total"] == 15
    assert report["setup_correct"] == 15
    assert report["setup_wrong"] == 0  # the load-bearing count
    assert report["setup_refused"] == 0


# --------------------------------------------------------------------------- #
# Obligation 2 — the oracle is not decoration (it catches wrong readings)
# --------------------------------------------------------------------------- #


def test_right_answer_wrong_structure_is_caught() -> None:
    # Gold: mia = liam + 4 over liam = 6  (answer 10, read as a relation).
    gold = [
        {"kind": "fact", "entity": "liam", "value": 6},
        {"kind": "more_than", "entity": "mia", "ref": "liam", "delta": 4},
    ]
    # A reading that lands on the SAME answer (mia = 10) but flattens the relation
    # into a bare fact — the right number, the wrong reading.
    wrong_structure = [{"kind": "fact", "entity": "mia", "value": 10}]
    assert relation_signature(gold) != relation_signature(wrong_structure)


def test_signature_catches_wrong_operation() -> None:
    more = [{"kind": "more_than", "entity": "y", "ref": "x", "delta": 6}]
    fewer = [{"kind": "fewer_than", "entity": "y", "ref": "x", "delta": 6}]
    assert relation_signature(more) != relation_signature(fewer)


def test_signature_is_order_independent() -> None:
    a = [
        {"kind": "fact", "entity": "x", "value": 1},
        {"kind": "more_than", "entity": "y", "ref": "x", "delta": 2},
    ]
    assert relation_signature(a) == relation_signature(list(reversed(a)))


def test_wrong_question_target_is_caught() -> None:
    rels = [
        {"kind": "fact", "entity": "dan", "value": 7},
        {"kind": "more_than", "entity": "eva", "ref": "dan", "delta": 9},
        {"kind": "sum_of", "entity": "total", "parts": ["dan", "eva"]},
    ]
    # Gold asks the total; a reader that targeted "eva" instead is a different reading.
    units = {"total": "item"}
    assert gold_unknown_signature(rels, {"entity": "total"}, units) == ("total", "terminal", "total", "item")
    assert gold_unknown_signature(rels, {"entity": "total"}, units) != ("eva", "terminal", "count", "item")


def test_malformed_graph_target_never_matches_gold() -> None:
    # A graph carrying no question target (pre-PR-1 shape) must report MALFORMED and
    # never silently compare equal to a well-formed gold target.
    graph = SemanticSymbolicBindingGraph(
        symbols=(SymbolBinding(symbol_id="x", name="x", semantic_role="count",
                               source_span=_span(), introduced_by="t", entity="x", unit="item"),),
        facts=(BoundFact(symbol_id="x", value="1", source_span=_span(), unit="item"),),
        equations=(),
        unknowns=(),
    )
    sig = reader_unknown_signature(graph)
    assert sig[0] == "MALFORMED"
    assert sig != ("x", "terminal", "count", "item")


# --------------------------------------------------------------------------- #
# PR-5a — the ruler is now UNIT-AWARE (structure can match while units diverge)
# --------------------------------------------------------------------------- #


def test_unit_mismatch_is_caught_even_when_structure_matches() -> None:
    # Same structure (a single fact about x), but the reader modelled a different unit.
    # The setup-oracle must FAIL — a unit-wrong reading is not a correct setup.
    gold_units = symbol_unit_signature({"x": "item"})
    reader_units_wrong = symbol_unit_signature({"x": "meter"})
    assert gold_units != reader_units_wrong
    assert symbol_unit_signature({"x": "item"}) == symbol_unit_signature({"x": "item"})


def test_target_unit_mismatch_is_caught() -> None:
    # Structure + symbol + state + form all agree, but the target's expected unit differs.
    rels = [{"kind": "fact", "entity": "x", "value": 1}]
    assert gold_unknown_signature(rels, {"entity": "x"}, {"x": "item"}) != gold_unknown_signature(
        rels, {"entity": "x"}, {"x": "dollars"}
    )


def test_reader_units_read_from_the_binding_graph() -> None:
    # The reader's unit signature comes from the GRAPH's symbols, not the answer projection.
    graph = SemanticSymbolicBindingGraph(
        symbols=(
            SymbolBinding(symbol_id="iris", name="iris", semantic_role="count",
                          source_span=_span(), introduced_by="t", entity="iris", unit="dollars"),
            SymbolBinding(symbol_id="jack", name="jack", semantic_role="count",
                          source_span=_span(), introduced_by="t", entity="jack", unit="dollars"),
        ),
        facts=(BoundFact(symbol_id="iris", value="100", source_span=_span(), unit="dollars"),),
        equations=(),
        unknowns=(BoundUnknown(symbol_id="jack", question_span=_span(), state_index="terminal",
                               question_form="count", expected_unit="dollars"),),
    )
    assert reader_symbol_units(graph) == (("iris", "dollars"), ("jack", "dollars"))
    assert reader_unknown_signature(graph) == ("jack", "terminal", "count", "dollars")


# --------------------------------------------------------------------------- #
# PR-5b — independent R1 gold: the reader must REFUSE, never MISREAD
# --------------------------------------------------------------------------- #


def test_r1_comparative_supported_rest_refused_wrong_zero() -> None:
    r = run_r1()
    assert r["total"] == 10
    # THE invariant through every capability slice: NO R1 case is misread. Each frame
    # turns refusals into correct readings without ever producing a setup_wrong.
    assert r["setup_wrong"] == 0
    by_id = {d["id"]: d["outcome"] for d in r["details"]}
    # Multiplicative frame (PR-5c): "twice as many" (r1-01) + the multi-step chain whose
    # middle step is "N times as many" (r1-05).
    assert by_id["r1-01-twice"] == "correct"
    assert by_id["r1-05-chain"] == "correct"
    # Divisive frame (PR-6c): "half as many" (r1-02).
    assert by_id["r1-02-half"] == "correct"
    # Partition frame (PR-6d): aggregate-then-divide "split equally into 3 boxes" (r1-06).
    assert by_id["r1-06-subtotal-reused"] == "correct"
    # Aggregate-query frame (aggregate-query slice): additive total asked via a trailing
    # qualifier — "altogether" (r1-03) and "in total" (r1-04). Phrasing-only widening of
    # the existing sum_of; no new arithmetic or relation kind.
    assert by_id["r1-03-more-total"] == "correct"
    assert by_id["r1-04-fewer-total"] == "correct"
    assert r["setup_correct"] == 6
    assert r["setup_refused"] == 4
    # No detail is ever WRONG, and every non-correct one is a typed refusal.
    for d in r["details"]:
        assert d["outcome"] in ("correct", "refused")
        if d["outcome"] == "refused":
            assert d.get("reason")


# --------------------------------------------------------------------------- #
# PR-6b — off-serving answer oracle support for times_as_many
# --------------------------------------------------------------------------- #


def test_oracle_computes_times_as_many_forward_only() -> None:
    assert oracle_answer(
        [
            {"kind": "fact", "entity": "anna", "value": 6},
            {"kind": "times_as_many", "entity": "bella", "ref": "anna", "factor": 2},
        ],
        {"entity": "bella"},
    ) == 12


def test_oracle_rejects_invalid_times_factor_and_forward_ref() -> None:
    with pytest.raises(OracleError):
        oracle_answer(
            [
                {"kind": "fact", "entity": "anna", "value": 6},
                {"kind": "times_as_many", "entity": "bella", "ref": "anna", "factor": 2.5},
            ],
            {"entity": "bella"},
        )
    with pytest.raises(OracleError):
        oracle_answer(
            [{"kind": "times_as_many", "entity": "bella", "ref": "anna", "factor": 2}],
            {"entity": "bella"},
        )


def test_r1_answer_lane_scores_only_setup_correct_fixtures() -> None:
    r = run_r1_answers()
    assert r["total"] == 10
    assert r["setup_wrong"] == 0
    assert r["wrong"] == 0
    assert r["gold_error"] == 0
    assert r["correct"] == 6
    assert r["refused"] == 4
    by_id = {d["id"]: d for d in r["details"]}
    assert by_id["r1-01-twice"] == {"id": "r1-01-twice", "outcome": "correct", "answer": 12}
    assert by_id["r1-02-half"] == {"id": "r1-02-half", "outcome": "correct", "answer": 4}
    assert by_id["r1-05-chain"] == {"id": "r1-05-chain", "outcome": "correct", "answer": 14}
    # PR-6d: the partition's derived per-box answer (total 12 / 3 boxes = 4).
    assert by_id["r1-06-subtotal-reused"] == {"id": "r1-06-subtotal-reused", "outcome": "correct", "answer": 4}
    # Aggregate-query slice: additive totals via "altogether" / "in total".
    assert by_id["r1-03-more-total"] == {"id": "r1-03-more-total", "outcome": "correct", "answer": 25}
    assert by_id["r1-04-fewer-total"] == {"id": "r1-04-fewer-total", "outcome": "correct", "answer": 34}
    _supported = {
        "r1-01-twice", "r1-02-half", "r1-05-chain", "r1-06-subtotal-reused",
        "r1-03-more-total", "r1-04-fewer-total",
    }
    for fixture_id, detail in by_id.items():
        if fixture_id not in _supported:
            assert detail["outcome"] == "refused"
            assert detail.get("reason")


# --------------------------------------------------------------------------- #
# PR-6c — off-serving answer oracle support for divide_by ("half as many")
# --------------------------------------------------------------------------- #


def test_oracle_computes_divide_by_exact() -> None:
    assert oracle_answer(
        [
            {"kind": "fact", "entity": "carl", "value": 8},
            {"kind": "divide_by", "entity": "dora", "ref": "carl", "divisor": 2},
        ],
        {"entity": "dora"},
    ) == 4


def test_oracle_refuses_non_exact_division() -> None:
    """The wrong=0 boundary of the divisive frame: a non-exact division REFUSES rather
    than flooring to a wrong integer. ``7 // 2 == 3`` would be WRONG; the oracle raises.

    Meaningful-fail: if the ``base % divisor != 0`` guard were dropped, this would return
    3 (a fabricated answer) instead of raising — the assert flips from pass to fail.
    """
    with pytest.raises(OracleError):
        oracle_answer(
            [
                {"kind": "fact", "entity": "xio", "value": 7},
                {"kind": "divide_by", "entity": "yon", "ref": "xio", "divisor": 2},
            ],
            {"entity": "yon"},
        )


def test_oracle_rejects_bad_divisor_and_forward_ref() -> None:
    """The full ``divide_by`` refusal contract — every bad-divisor / unresolved-base class
    raises ``OracleError`` (never a ZeroDivisionError, never a silent float/floor)."""
    base = {"kind": "fact", "entity": "carl", "value": 8}

    def _bad_divisor(divisor: object) -> None:
        with pytest.raises(OracleError):
            oracle_answer(
                [base, {"kind": "divide_by", "entity": "dora", "ref": "carl", "divisor": divisor}],
                {"entity": "dora"},
            )

    _bad_divisor(0.5)   # non-integer (fractional < 1)
    _bad_divisor(1.5)   # non-integer (fractional > 1)
    _bad_divisor(0)     # zero divisor — never ZeroDivisionError
    _bad_divisor(True)  # bool is not an admissible int divisor (isinstance(True, int) is True)
    # Forward reference to an unresolved base → refuse.
    with pytest.raises(OracleError):
        oracle_answer(
            [{"kind": "divide_by", "entity": "dora", "ref": "carl", "divisor": 2}],
            {"entity": "dora"},
        )


def test_oracle_divide_by_one_is_identity() -> None:
    """``divisor=1`` is intentionally ALLOWED: base / 1 = base, exact. The reader never
    constructs it (``_DIVISOR_WORDS`` only maps 'half'→2), but the oracle's grammar admits
    it mathematically. Pinned so the choice stays deliberate, not accidental."""
    assert oracle_answer(
        [
            {"kind": "fact", "entity": "carl", "value": 8},
            {"kind": "divide_by", "entity": "dora", "ref": "carl", "divisor": 1},
        ],
        {"entity": "dora"},
    ) == 8


# --------------------------------------------------------------------------- #
# PR-7a — narrow reverse-solve oracle contract (the base of one more/fewer_than).
# Pins the EXACT semantics before the reader learns the inverse frame (PR-7b). The
# reader is unchanged here: r1-07 still refuses; these exercise the oracle directly.
# Each refusal is meaningful-fail — drop its guardrail and the case computes a value.
# --------------------------------------------------------------------------- #


def _F(e, v):
    return {"kind": "fact", "entity": e, "value": v}


def _M(e, r, d):
    return {"kind": "more_than", "entity": e, "ref": r, "delta": d}


def _W(e, r, d):
    return {"kind": "fewer_than", "entity": e, "ref": r, "delta": d}


def test_oracle_reverse_solves_more_than_base() -> None:
    # Nia has 9 more beads than Omar. Nia has 15. -> omar = 15 - 9 = 6.  (r1-07 gold)
    assert oracle_answer([_F("nia", 15), _M("nia", "omar", 9)], {"entity": "omar"}) == 6


def test_oracle_reverse_solves_fewer_than_base() -> None:
    # Pat has 3 fewer than Quinn. Pat has 4. -> quinn = 4 + 3 = 7.
    assert oracle_answer([_F("pat", 4), _W("pat", "quinn", 3)], {"entity": "quinn"}) == 7


def test_r1_07_gold_relations_reverse_solve_to_six() -> None:
    # The exact gold relations the PR-7b answer lane will feed the oracle compute gold=6.
    from evals.setup_oracle.runner import _load_r1_gold

    fx = next(f for f in run_r1()["details"] if f["id"] == "r1-07-inverse")
    assert fx["outcome"] == "refused"  # reader still refuses in PR-7a (contract only)
    gold = next(g for g in _load_r1_gold() if g["id"] == "r1-07-inverse")
    assert oracle_answer(gold["relations"], gold["query"]) == gold["gold"] == 6


def test_oracle_reverse_solve_refuses_negative_count() -> None:
    # Nia has 9 more than Omar. Nia has 5. -> omar = -4 < 0: refuse, never a negative count.
    with pytest.raises(OracleError):
        oracle_answer([_F("nia", 5), _M("nia", "omar", 9)], {"entity": "omar"})


def test_oracle_reverse_solve_refuses_multiple_bases() -> None:
    # Two inverse constraints -> not a single base: refuse (no multi-inverse / no system).
    with pytest.raises(OracleError):
        oracle_answer(
            [_F("a", 10), _F("b", 8), _M("a", "x", 2), _M("b", "x", 1)], {"entity": "x"}
        )


def test_oracle_reverse_solve_refuses_grounded_base() -> None:
    # The base is otherwise grounded -> over-determined: refuse rather than ignore a side.
    with pytest.raises(OracleError):
        oracle_answer(
            [_F("nia", 15), _F("omar", 6), _M("nia", "omar", 9)], {"entity": "omar"}
        )


def test_oracle_reverse_solve_refuses_base_not_target() -> None:
    # The inverse base is not the asked entity (a chain): refuse, never solve through.
    with pytest.raises(OracleError):
        oracle_answer([_F("nia", 15), _M("nia", "omar", 9)], {"entity": "zed"})


def test_oracle_reverse_solve_refuses_over_times_as_many() -> None:
    # No reverse-solve over times_as_many: Nia has twice as many as Omar; Nia has 14 -> refuse.
    with pytest.raises(OracleError):
        oracle_answer(
            [_F("nia", 14), {"kind": "times_as_many", "entity": "nia", "ref": "omar", "factor": 2}],
            {"entity": "omar"},
        )


def test_oracle_forward_paths_unchanged_by_reverse_solve() -> None:
    # Regression guard: every forward path still computes (the duplicate-check refactor
    # must not perturb forward more/fewer/times/divide/sum).
    assert oracle_answer([_F("a", 6), _M("b", "a", 4)], {"entity": "b"}) == 10
    assert oracle_answer([_F("a", 6), _W("b", "a", 4)], {"entity": "b"}) == 2
    assert oracle_answer(
        [_F("a", 6), {"kind": "times_as_many", "entity": "b", "ref": "a", "factor": 3}],
        {"entity": "b"},
    ) == 18
    assert oracle_answer(
        [_F("a", 8), {"kind": "divide_by", "entity": "b", "ref": "a", "divisor": 2}],
        {"entity": "b"},
    ) == 4
    assert oracle_answer(
        [_F("a", 6), _F("b", 4), {"kind": "sum_of", "entity": "t", "parts": ["a", "b"]}],
        {"entity": "t"},
    ) == 10
