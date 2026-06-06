"""Typed expression IR (PR-4) — the reader's source of meaning for an equation rhs.

Pins: the canonical serialization is byte-identical to the pre-IR string format (so the
binding-graph + every downstream hash is unchanged), the structured projection reads the
IR (never the string), and dependencies/operation_kind derive from the IR.
"""

from __future__ import annotations

from generate.quantitative_comprehension import comprehend_quantitative
from generate.quantitative_expr import (
    Add,
    Literal,
    Sub,
    SumOf,
    Symbol,
    dependencies,
    operation_kind,
    to_canonical_string,
    to_relation,
)


def test_canonical_string_is_byte_identical_to_legacy_format() -> None:
    assert to_canonical_string(Add(Symbol("liam"), Literal(4))) == "liam + 4"
    assert to_canonical_string(Sub(Symbol("noah"), Literal(6))) == "noah - 6"
    assert to_canonical_string(SumOf((Symbol("dan"), Symbol("eva")))) == "dan + eva"
    assert to_canonical_string(Symbol("x")) == "x"
    assert to_canonical_string(Literal(7)) == "7"


def test_dependencies_from_structure() -> None:
    assert dependencies(Add(Symbol("liam"), Literal(4))) == frozenset({"liam"})
    assert dependencies(Sub(Symbol("noah"), Literal(6))) == frozenset({"noah"})
    assert dependencies(SumOf((Symbol("dan"), Symbol("eva")))) == frozenset({"dan", "eva"})
    assert dependencies(Literal(3)) == frozenset()


def test_operation_kind_from_structure() -> None:
    assert operation_kind(Add(Symbol("a"), Literal(1))) == "add"
    assert operation_kind(SumOf((Symbol("a"), Symbol("b")))) == "add"
    assert operation_kind(Sub(Symbol("a"), Literal(1))) == "subtract"


def test_to_relation_reads_structure_not_string() -> None:
    assert to_relation("mia", Add(Symbol("liam"), Literal(4))) == {
        "kind": "more_than", "entity": "mia", "ref": "liam", "delta": 4,
    }
    assert to_relation("olivia", Sub(Symbol("noah"), Literal(6))) == {
        "kind": "fewer_than", "entity": "olivia", "ref": "noah", "delta": 6,
    }
    assert to_relation("total", SumOf((Symbol("dan"), Symbol("eva")))) == {
        "kind": "sum_of", "entity": "total", "parts": ["dan", "eva"],
    }


def test_to_relation_refuses_unhandled_shape() -> None:
    # A literal-only or nested shape the projection doesn't handle returns None (refuse).
    assert to_relation("x", Literal(5)) is None
    assert to_relation("x", Add(Literal(1), Literal(2))) is None  # no symbol ref


def test_reader_carries_ir_consistent_with_rhs_canonical() -> None:
    # The IR the reader attaches serializes EXACTLY to the equation's rhs_canonical.
    comp = comprehend_quantitative(
        "Liam has 6 stickers. Mia has 4 more stickers than Liam. How many stickers does Mia have?"
    )
    by_lhs = {lhs: expr for lhs, expr in comp.equation_exprs}
    for eq in comp.binding_graph.equations:
        assert to_canonical_string(by_lhs[eq.lhs_symbol_id]) == eq.rhs_canonical
        assert dependencies(by_lhs[eq.lhs_symbol_id]) == eq.dependencies
