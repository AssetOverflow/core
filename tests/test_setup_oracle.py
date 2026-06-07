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


def test_r1_multiplicative_supported_rest_refused_wrong_zero() -> None:
    r = run_r1()
    assert r["total"] == 10
    # THE invariant through the first capability slice: NO R1 case is misread. Adding the
    # multiplicative frame turned refusals into correct readings without any setup_wrong.
    assert r["setup_wrong"] == 0
    # The multiplicative frame (PR-5c) reads "twice as many" (r1-01) and the multi-step
    # chain whose middle step is "N times as many" (r1-05); the rest stay safe refusals.
    by_id = {d["id"]: d["outcome"] for d in r["details"]}
    assert by_id["r1-01-twice"] == "correct"
    assert by_id["r1-05-chain"] == "correct"
    assert r["setup_correct"] == 2
    assert r["setup_refused"] == 8
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
    assert r["correct"] == 2
    assert r["refused"] == 8
    by_id = {d["id"]: d for d in r["details"]}
    assert by_id["r1-01-twice"] == {"id": "r1-01-twice", "outcome": "correct", "answer": 12}
    assert by_id["r1-05-chain"] == {"id": "r1-05-chain", "outcome": "correct", "answer": 14}
    for fixture_id, detail in by_id.items():
        if fixture_id not in {"r1-01-twice", "r1-05-chain"}:
            assert detail["outcome"] == "refused"
            assert detail.get("reason")
