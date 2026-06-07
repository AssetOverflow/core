"""Unit tests for the arithmetic reader (prose -> binding_graph) + its projector.

Pins the templates, the count-vs-physical-unit modelling, and — load-bearing — the
REAL admissibility check: an equation is admitted only if its operand units verify,
so a mixed-unit sum REFUSES rather than fabricating a quantity. This is the
reviewer's "do not stamp admissibility" guard, made executable.
"""

from __future__ import annotations

import pytest

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


def test_half_as_many_builds_divide_equation() -> None:
    # PR-6c: "half as many" is the divisive twin of "twice as many" — operation_kind
    # "divide", a single symbol dep (the divisor literal is in the IR, not a graph symbol),
    # and the REAL single-dep admissibility check (item / dimensionless = item) admits it.
    comp = _comp("Carl has 8 coins. Dora has half as many coins as Carl. How many coins does Dora have?")
    eq = next(e for e in comp.binding_graph.equations if e.lhs_symbol_id == "dora")
    assert eq.operation_kind == "divide"
    assert eq.rhs_canonical == "carl / 2"
    assert eq.dependencies == frozenset({"carl"})  # uniform with Mul: literal not a dep
    assert eq.admissibility_status == "admitted"
    assert single_unknown(comp.binding_graph).symbol_id == "dora"
    # The graph carries ONLY the two entities — no synthesized __divisor symbol pollutes
    # it (that is why the symmetric single-dep divide was chosen over divisor synthesis).
    assert {s.symbol_id for s in comp.binding_graph.symbols} == {"carl", "dora"}


def test_half_as_many_missing_base_refuses() -> None:
    # "half as many ... as Rod" with no value for Rod -> ungrounded base -> REFUSE.
    comp = comprehend_quantitative("Sue has half as many pears as Rod. How many pears does Sue have?")
    assert isinstance(comp, Refusal)


# --------------------------------------------------------------------------- #
# PR-6d — aggregate-then-divide partition (SumOf + Div, no new relation kind)
# --------------------------------------------------------------------------- #

_PARTITION_TEXT = (
    "Lee has 5 hats. Mae has 7 hats. They combine their hats and split them "
    "equally into 3 boxes. How many hats are in each box?"
)


def test_partition_builds_sum_then_divide() -> None:
    # PR-6d: one sentence synthesizes TWO derived symbols — total = lee + mae (sum_of)
    # and per_box = total / 3 (divide_by, the FIRST divide whose ref is itself derived).
    comp = _comp(_PARTITION_TEXT)
    by_lhs = {e.lhs_symbol_id: e for e in comp.binding_graph.equations}
    total = by_lhs["total"]
    assert total.operation_kind == "add"
    assert total.rhs_canonical == "lee + mae"
    assert total.dependencies == frozenset({"lee", "mae"})
    per_box = by_lhs["per_box"]
    assert per_box.operation_kind == "divide"
    assert per_box.rhs_canonical == "total / 3"
    assert per_box.dependencies == frozenset({"total"})  # ref is a DERIVED symbol
    assert total.admissibility_status == per_box.admissibility_status == "admitted"
    assert single_unknown(comp.binding_graph).symbol_id == "per_box"
    # Only the modelled entities — the partition introduces no proof-machinery symbol.
    assert {s.symbol_id for s in comp.binding_graph.symbols} == {"lee", "mae", "total", "per_box"}


def test_partition_without_its_query_refuses() -> None:
    # A partition sentence whose question is a plain "does X have" (not "in each box")
    # is incoherent -> REFUSE, never read a dangling partition.
    comp = comprehend_quantitative(
        "Lee has 5 hats. Mae has 7 hats. They combine their hats and split them "
        "equally into 3 boxes. How many hats does Lee have?"
    )
    assert isinstance(comp, Refusal)


def test_per_each_query_without_partition_refuses() -> None:
    # "in each box" with no partition sentence -> no per-box symbol exists -> REFUSE.
    comp = comprehend_quantitative("Lee has 5 hats. How many hats are in each box?")
    assert isinstance(comp, Refusal)


def test_partition_container_mismatch_refuses() -> None:
    # Split into boxes but asked "in each jar" -> container mismatch -> REFUSE.
    comp = comprehend_quantitative(
        "Lee has 5 hats. Mae has 7 hats. They combine their hats and split them "
        "equally into 3 boxes. How many hats are in each jar?"
    )
    assert isinstance(comp, Refusal)


def test_partition_setup_correct_but_non_exact_answer_refuses() -> None:
    # The reading is correct (total = 5 + 6, per_box = total / 3), but 11 % 3 != 0, so
    # the answer oracle REFUSES — exact-divisibility still gates the partition's answer.
    from evals.relational_metric.oracle import OracleError, oracle_answer

    comp = _comp(
        "Lee has 5 hats. Mae has 6 hats. They combine their hats and split them "
        "equally into 3 boxes. How many hats are in each box?"
    )
    projected = to_relational_metric(comp)
    assert projected is not None  # the SETUP is readable
    relations, query = projected
    with pytest.raises(OracleError):  # but 11 / 3 is non-exact -> the answer refuses
        oracle_answer(relations, query)


# --------------------------------------------------------------------------- #
# Additive aggregate query variants: "... have altogether?" / "... have in total?"
# A trailing qualifier after "have" is stripped and honored ONLY for the multi-part
# aggregate (sumquery) form. No new arithmetic, no new relation kind: the parts flow
# through sum_of, and admissibility still gates grounding + unit-compatibility.
# --------------------------------------------------------------------------- #


def test_aggregate_query_altogether_reads_and_sums() -> None:
    from evals.relational_metric.oracle import oracle_answer

    comp = _comp(
        "Finn has 10 books. Evan has 5 more books than Finn. "
        "How many books do Evan and Finn have altogether?"
    )
    assert single_unknown(comp.binding_graph).symbol_id == "total"
    total_eq = next(e for e in comp.binding_graph.equations if e.lhs_symbol_id == "total")
    assert total_eq.operation_kind == "add"
    assert set(total_eq.dependencies) == {"evan", "finn"}
    relations, query = to_relational_metric(comp)
    assert oracle_answer(relations, query) == 25  # evan=15, finn=10


def test_aggregate_query_in_total_reads_and_sums() -> None:
    from evals.relational_metric.oracle import oracle_answer

    comp = _comp(
        "Gail has 20 cards. Hank has 6 fewer cards than Gail. "
        "How many cards do Gail and Hank have in total?"
    )
    assert single_unknown(comp.binding_graph).symbol_id == "total"
    relations, query = to_relational_metric(comp)
    assert oracle_answer(relations, query) == 34  # gail=20, hank=14


def test_aggregate_qualifier_on_single_entity_refuses() -> None:
    # The qualifier is honored ONLY for the multi-part form. A single-entity query
    # carrying "altogether" is nonsensical and must REFUSE. This is load-bearing: the
    # ``not aggregate`` guard is what blocks the "does X have" template from firing on
    # an aggregate-qualified question and silently reading a single grounded fact.
    comp = comprehend_quantitative("Anna has 6 apples. How many apples does Anna have altogether?")
    assert isinstance(comp, Refusal)
    assert comp.reason == "unreadable_quantity_query"


def test_aggregate_query_ungrounded_part_refuses() -> None:
    # Widening the recognizer cannot admit an UNGROUNDED part: "zoe" has no fact or
    # derivation, so its unit is unbound and the sum's admissibility REFUSES rather than
    # fabricating a partial total. (wrong=0 boundary — the recognizer over-reads the
    # surface, admissibility refuses to ground it.)
    comp = comprehend_quantitative(
        "Finn has 10 books. Evan has 5 more books than Finn. "
        "How many books do Evan and Zoe have altogether?"
    )
    assert isinstance(comp, Refusal)
    assert comp.reason == "admissibility_refused"
    assert "unit_unbound" in comp.detail


def test_aggregate_query_unit_incompatible_part_refuses() -> None:
    # ... and cannot admit UNIT-INCOMPATIBLE parts: dollars (currency) + books (item)
    # is a mixed-dimension sum, refused by the REAL additive unit check.
    comp = comprehend_quantitative(
        "Anna has 5 dollars. Bella has 3 books. "
        "How many books do Anna and Bella have altogether?"
    )
    assert isinstance(comp, Refusal)
    assert comp.reason == "admissibility_refused"
    assert "unit_mismatch" in comp.detail


# --------------------------------------------------------------------------- #
# Inverse frame (PR-7b): a more/fewer-than whose SUBJECT is a known fact and whose
# REFERENT is the otherwise-ungrounded query target pins the unknown base. The base's
# unit is bound FROM the relation so the equation is admissible; the answer oracle
# reverse-solves the value (PR-7a). Bounded — single base == query target, known subject,
# base not otherwise grounded, <=1 inverse, never over times/divide.
# --------------------------------------------------------------------------- #


def test_inverse_more_than_reads_base_with_bound_unit() -> None:
    from evals.relational_metric.oracle import oracle_answer

    # Nia has 9 more beads than Omar. Nia has 15 beads. How many beads does Omar have?
    comp = _comp("Nia has 9 more beads than Omar. Nia has 15 beads. How many beads does Omar have?")
    # The base (omar) carries the relation's unit even though it has no fact of its own.
    units = {s.symbol_id: s.unit for s in comp.binding_graph.symbols}
    assert units == {"nia": "item", "omar": "item"}
    assert single_unknown(comp.binding_graph).symbol_id == "omar"
    relations, query = to_relational_metric(comp)
    assert query == {"entity": "omar", "unit": "item"}
    assert {"kind": "fact", "entity": "nia", "value": 15} in relations
    assert {"kind": "more_than", "entity": "nia", "ref": "omar", "delta": 9} in relations
    assert oracle_answer(relations, query) == 6  # omar = 15 - 9


def test_inverse_fewer_than_reads_base() -> None:
    from evals.relational_metric.oracle import oracle_answer

    # Quinn has 4 fewer beads than Pat. Quinn has 10 beads. How many beads does Pat have?
    comp = _comp("Quinn has 4 fewer beads than Pat. Quinn has 10 beads. How many beads does Pat have?")
    assert single_unknown(comp.binding_graph).symbol_id == "pat"
    relations, query = to_relational_metric(comp)
    assert oracle_answer(relations, query) == 14  # pat = 10 + 4


def test_inverse_base_must_be_query_target_refuses() -> None:
    # The unknown base (omar) is NOT what's asked — the question asks the grounded subject
    # while the base stays unbound. No inverse fires (ref != query target); the equation's
    # ungrounded operand makes admissibility REFUSE rather than guess. (no chains)
    comp = comprehend_quantitative(
        "Nia has 9 more beads than Omar. Nia has 15 beads. How many beads does Nia have?"
    )
    assert isinstance(comp, Refusal)
    assert comp.reason == "admissibility_refused"


def test_multiple_inverse_bases_refuses() -> None:
    # Two known subjects each pin the SAME unknown base -> an over-determined inverse, not a
    # single base. The reader REFUSES rather than bind from one and drop the other. Without
    # the len>1 guard this would emit a setup the oracle then chokes on; refusing is honest.
    comp = comprehend_quantitative(
        "Nia has 9 more beads than Omar. Pam has 5 more beads than Omar. "
        "Nia has 15 beads. Pam has 11 beads. How many beads does Omar have?"
    )
    assert isinstance(comp, Refusal)
    assert comp.reason == "multiple_inverse_bases"


def test_inverse_over_times_as_many_refuses() -> None:
    # The inverse frame is add/subtract ONLY. A times-as-many with an ungrounded ref is
    # never reverse-solved: the ref stays unit-unbound and admissibility REFUSES.
    comp = comprehend_quantitative(
        "Nia has twice as many beads as Omar. Nia has 14 beads. How many beads does Omar have?"
    )
    assert isinstance(comp, Refusal)
    assert comp.reason == "admissibility_refused"
