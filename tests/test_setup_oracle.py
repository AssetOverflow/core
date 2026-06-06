"""Setup-oracle lane — grade the reading (structure), not the answer.

Two obligations:
1. The current reader reads all 15 relational_metric cases with the gold STRUCTURE
   (``setup_wrong == 0``) — the gate the milestone rests on.
2. The oracle MEANINGFULLY FAILS — a reading that lands on the right number via the
   WRONG structure is ``setup_wrong``. Without this, structure-grading would be
   decoration; with it, "did we read it right?" is falsifiable.
"""

from __future__ import annotations

from evals.setup_oracle import (
    gold_unknown_signature,
    reader_unknown_signature,
    relation_signature,
    run,
)
from generate.binding_graph.model import (
    BoundFact,
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
    assert gold_unknown_signature(rels, {"entity": "total"}) == ("total", "terminal", "total")
    assert gold_unknown_signature(rels, {"entity": "total"}) != ("eva", "terminal", "count")


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
    assert sig != ("x", "terminal", "count")
