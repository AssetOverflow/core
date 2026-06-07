"""Unit tests for the arithmetic reader (prose -> binding_graph) + its projector.

Pins the templates, the count-vs-physical-unit modelling, and — load-bearing — the
REAL admissibility check: an equation is admitted only if its operand units verify,
so a mixed-unit sum REFUSES rather than fabricating a quantity. This is the
reviewer's "do not stamp admissibility" guard, made executable.
"""

from __future__ import annotations

from generate.binding_graph.model import (
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
)
from generate.meaning_graph.reader import Refusal
from generate.quantitative_comprehension import (
    QuantComprehension,
    comprehend_quantitative,
    single_unknown,
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
    assert single_unknown(g).symbol_id == "mia"


def test_question_target_is_a_bound_unknown_in_the_graph() -> None:
    # The question target lives INSIDE the graph (a BoundUnknown at the terminal
    # state) — read via single_unknown, never a sidecar field (PR-3 removed QuantQuery).
    comp = _comp("Liam has 6 stickers. Mia has 4 more stickers than Liam. How many stickers does Mia have?")
    u = single_unknown(comp.binding_graph)
    assert u is not None
    assert u.symbol_id == "mia"
    assert u.state_index == "terminal"
    assert u.question_form == "count"
    assert u.expected_unit == "item"
    # The graph's canonical serialization carries the target.
    assert "state=terminal" in comp.binding_graph.to_canonical_string()


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


def test_sum_query_target_via_single_unknown() -> None:
    comp = _comp("Dan has 7 coins. Eva has 9 more coins than Dan. How many coins do Dan and Eva have?")
    assert single_unknown(comp.binding_graph).symbol_id == "total"


def test_sum_query_synthesizes_total() -> None:
    comp = _comp("Dan has 7 coins. Eva has 9 more coins than Dan. How many coins do Dan and Eva have?")
    assert single_unknown(comp.binding_graph).symbol_id == "total"
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


# --------------------------------------------------------------------------- #
# PR-3 — malformed graphs REFUSE (never pick one of several targets)
# --------------------------------------------------------------------------- #


def _sp() -> SourceSpanLink:
    return SourceSpanLink(source_id="t", start=0, end=1, text="x")


def _graph_with_n_unknowns(n: int) -> SemanticSymbolicBindingGraph:
    symbols = tuple(
        SymbolBinding(symbol_id=s, name=s, semantic_role="count",
                      source_span=_sp(), introduced_by="t", entity=s, unit="item")
        for s in ("a", "b")
    )
    unknowns = tuple(
        BoundUnknown(symbol_id=s, question_span=_sp(), state_index="terminal",
                     question_form="count", expected_unit="item")
        for s in ("a", "b")[:n]
    )
    return SemanticSymbolicBindingGraph(
        symbols=symbols,
        facts=(BoundFact(symbol_id="a", value="1", source_span=_sp(), unit="item"),),
        equations=(),
        unknowns=unknowns,
    )


def test_single_unknown_refuses_zero_and_multiple() -> None:
    assert single_unknown(_graph_with_n_unknowns(0)) is None  # no question target
    assert single_unknown(_graph_with_n_unknowns(2)) is None  # ambiguous → refuse, not pick
    assert single_unknown(_graph_with_n_unknowns(1)) is not None


def test_to_relational_metric_refuses_malformed_target() -> None:
    for n in (0, 2):
        comp = QuantComprehension(binding_graph=_graph_with_n_unknowns(n))
        assert to_relational_metric(comp) is None  # refuse rather than emit a guessed query


# --------------------------------------------------------------------------- #
# PR-5c — the multiplicative comparative frame ("twice / N times as many")
# --------------------------------------------------------------------------- #


def test_twice_as_many_builds_multiply_equation() -> None:
    comp = _comp("Anna has 6 apples. Bella has twice as many apples as Anna. How many apples does Bella have?")
    eq = next(e for e in comp.binding_graph.equations if e.lhs_symbol_id == "bella")
    assert eq.operation_kind == "multiply"
    assert eq.rhs_canonical == "anna * 2"
    assert eq.admissibility_status == "admitted"  # count * scalar = count, REAL check
    assert single_unknown(comp.binding_graph).symbol_id == "bella"


def test_n_times_as_many_builds_multiply_equation() -> None:
    comp = _comp("Ivy has 4 pens. Jon has 3 times as many pens as Ivy. How many pens does Jon have?")
    eq = next(e for e in comp.binding_graph.equations if e.lhs_symbol_id == "jon")
    assert eq.operation_kind == "multiply" and eq.rhs_canonical == "ivy * 3"


def test_multiplicative_missing_base_refuses() -> None:
    # "twice as many as Rosa" with no value for Rosa -> Rosa is ungrounded -> REFUSE,
    # never fabricate a base quantity.
    comp = comprehend_quantitative("Quinn has twice as many toys as Rosa. How many toys does Quinn have?")
    assert isinstance(comp, Refusal)
