"""Unit tests for the arithmetic reader (prose -> binding_graph) + its projector.

Pins the templates, the count-vs-physical-unit modelling, and — load-bearing — the
REAL admissibility check: an equation is admitted only if its operand units verify,
so a mixed-unit sum REFUSES rather than fabricating a quantity. This is the
reviewer's "do not stamp admissibility" guard, made executable.
"""

from __future__ import annotations

from generate.binding_graph.model import SemanticSymbolicBindingGraph
from generate.meaning_graph.reader import Refusal
from generate.quantitative_comprehension import (
    QuantComprehension,
    comprehend_quantitative,
    to_relational_metric,
)


def _comp(text: str) -> QuantComprehension:
    comp = comprehend_quantitative(text)
    assert isinstance(comp, QuantComprehension), comp
    return comp


def test_fact_and_more_than_build_binding_graph() -> None:
    comp = _comp("Liam has 6 stickers. Mia has 4 more stickers than Liam. How many stickers does Mia have?")
    g = comp.binding_graph
    assert isinstance(g, SemanticSymbolicBindingGraph)
    assert {f.symbol_id: f.value for f in g.facts} == {"liam": "6"}
    eq = next(e for e in g.equations if e.lhs_symbol_id == "mia")
    assert eq.operation_kind == "add"
    assert eq.rhs_canonical == "liam + 4"
    assert eq.admissibility_status == "admitted"  # from the REAL check, not stamped
    assert comp.query.entity == "mia"


def test_question_target_is_a_bound_unknown_in_the_graph() -> None:
    # PR-1: the question target lives INSIDE the graph (a BoundUnknown at the terminal
    # state), not only as the external QuantQuery.
    comp = _comp("Liam has 6 stickers. Mia has 4 more stickers than Liam. How many stickers does Mia have?")
    unknowns = comp.binding_graph.unknowns
    assert len(unknowns) == 1
    u = unknowns[0]
    assert u.symbol_id == "mia"
    assert u.state_index == "terminal"
    assert u.question_form == "count"
    assert u.expected_unit == "item"
    # The graph's canonical serialization now carries the target.
    assert "state=terminal" in comp.binding_graph.to_canonical_string()
    # Retained convenience stays consistent with the in-graph unknown.
    assert comp.query.entity == u.symbol_id


def test_sum_query_target_is_total_form_unknown() -> None:
    comp = _comp("Dan has 7 coins. Eva has 9 more coins than Dan. How many coins do Dan and Eva have?")
    (u,) = comp.binding_graph.unknowns
    assert u.symbol_id == "total" and u.question_form == "total" and u.state_index == "terminal"


def test_count_nouns_resolve_to_item_dimension() -> None:
    # Unknown sortal nouns become the count dimension (item); admissibility admits.
    comp = _comp("Kim has 2 marbles. Leo has 3 more marbles than Kim. How many marbles does Leo have?")
    units = {s.symbol_id: s.unit for s in comp.binding_graph.symbols}
    assert units["kim"] == "item" and units["leo"] == "item"


def test_known_unit_is_used_verbatim() -> None:
    comp = _comp("Iris has 100 dollars. Jack has 250 more dollars than Iris. How many dollars does Jack have?")
    units = {s.symbol_id: s.unit for s in comp.binding_graph.symbols}
    assert units["iris"] == "dollars"  # parse_unit depluralizes dollars -> dollar (money)


def test_fewer_than_is_subtract() -> None:
    comp = _comp("Noah has 15 cards. Olivia has 6 fewer cards than Noah. How many cards does Olivia have?")
    eq = next(e for e in comp.binding_graph.equations if e.lhs_symbol_id == "olivia")
    assert eq.operation_kind == "subtract" and eq.rhs_canonical == "noah - 6"


def test_sum_query_synthesizes_total() -> None:
    comp = _comp("Dan has 7 coins. Eva has 9 more coins than Dan. How many coins do Dan and Eva have?")
    assert comp.query.entity == "total"
    total_eq = next(e for e in comp.binding_graph.equations if e.lhs_symbol_id == "total")
    assert total_eq.operation_kind == "add"
    assert set(total_eq.dependencies) == {"dan", "eva"}


def test_projection_shape() -> None:
    comp = _comp("Liam has 6 stickers. Mia has 4 more stickers than Liam. How many stickers does Mia have?")
    projected = to_relational_metric(comp)
    assert projected is not None
    relations, query = projected
    assert {"kind": "fact", "entity": "liam", "value": 6} in relations
    assert {"kind": "more_than", "entity": "mia", "ref": "liam", "delta": 4} in relations
    assert query["entity"] == "mia"


# --------------------------------------------------------------------------- #
# Admissibility is REAL, not stamped (the reviewer's load-bearing guard)
# --------------------------------------------------------------------------- #


def test_mixed_unit_sum_refuses_via_admissibility() -> None:
    # count (stickers -> item) + money (dollars) cannot be summed: the REAL
    # admissibility check must REFUSE, not fabricate a total.
    comp = comprehend_quantitative(
        "Liam has 6 stickers. Mia has 4 dollars. How many things do Liam and Mia have?"
    )
    assert isinstance(comp, Refusal)
    assert comp.reason == "admissibility_refused"
    assert "unit_mismatch" in comp.detail


def test_non_digit_quantity_refuses() -> None:
    comp = comprehend_quantitative("Liam has several stickers. How many stickers does Liam have?")
    assert isinstance(comp, Refusal)
    assert comp.reason == "non_digit_quantity"


def test_unreadable_clause_refuses() -> None:
    comp = comprehend_quantitative("The weather is nice today.")
    assert isinstance(comp, Refusal)
