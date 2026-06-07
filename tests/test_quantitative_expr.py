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


# --------------------------------------------------------------------------- #
# PR-5c — the multiplicative comparative (Mul)
# --------------------------------------------------------------------------- #


def test_mul_serialization_and_derivations() -> None:
    from generate.quantitative_expr import Mul

    m = Mul(Symbol("anna"), Literal(2))
    assert to_canonical_string(m) == "anna * 2"
    assert dependencies(m) == frozenset({"anna"})
    assert operation_kind(m) == "multiply"
    assert to_relation("bella", m) == {
        "kind": "times_as_many", "entity": "bella", "ref": "anna", "factor": 2,
    }


# --------------------------------------------------------------------------- #
# PR-6a — the scalar-only contract is PROVEN, not held by omission
# --------------------------------------------------------------------------- #


def test_mul_projection_admits_only_symbol_times_literal() -> None:
    """``Mul(Symbol, Literal)`` is the ONLY shape that projects to ``times_as_many``;
    every other ``Mul`` shape REFUSES (``to_relation`` → None).

    Meaningful-fail (CLAUDE.md Schema-Defined Proof Obligations): each assert below
    fails loudly the moment the scalar-only guard is loosened — e.g. if a
    ``case Mul(Symbol(ref), Symbol(other))`` arm were added, a ``count × count`` product
    would masquerade as "N times as many". The dimensional checker does NOT catch this
    (``test_scalar_only_guard_is_load_bearing`` shows why), so this projection arm is the
    sole boundary.
    """
    from generate.quantitative_expr import Mul

    # The one admitted shape — the contrast case.
    assert to_relation("y", Mul(Symbol("x"), Literal(3))) == {
        "kind": "times_as_many", "entity": "y", "ref": "x", "factor": 3,
    }
    # Two unit-bearing symbols: a count×count product, NOT a scalar multiple → refuse.
    assert to_relation("y", Mul(Symbol("a"), Symbol("b"))) is None
    # Commuted (factor on the left): the reader only ever builds Symbol*Literal → refuse.
    assert to_relation("y", Mul(Literal(2), Symbol("a"))) is None
    # A compound (non-literal) factor → refuse.
    assert to_relation("y", Mul(Symbol("a"), Add(Symbol("b"), Literal(1)))) is None
    assert to_relation("y", Mul(Symbol("a"), SumOf((Symbol("b"), Symbol("c"))))) is None
    # A bare literal product carries no symbol to reference → refuse.
    assert to_relation("y", Mul(Literal(2), Literal(3))) is None


def test_literal_factor_is_dimensionless_by_construction() -> None:
    """A literal factor cannot carry a unit: ``Literal`` has exactly one field, ``value``.

    "Unit-bearing literal multiplication" is structurally unrepresentable — not merely
    unchecked. ``count × scalar = count`` holds because the scalar is an ``int`` with no
    unit, so the product keeps exactly the referenced symbol's unit. If a ``unit`` field
    were ever added to ``Literal``, this test fails and forces the contract to be revisited.
    """
    import dataclasses

    assert [f.name for f in dataclasses.fields(Literal)] == ["value"]
    assert not hasattr(Literal(2), "unit")


def test_scalar_only_guard_is_load_bearing() -> None:
    """WHY the projection arm (not the dimensional checker) owns the scalar-only contract.

    ``check_admissibility``'s ``multiply`` dispatch products operand units with no equality
    requirement, so a ``count × count`` equation is dimensionally ADMISSIBLE (it yields
    ``count²``). It would never refuse a two-symbol multiply. Hence the refusal in
    :func:`to_relation` is load-bearing — it is the only thing standing between a
    ``Mul(Symbol, Symbol)`` and a fabricated ``times_as_many`` relation.
    """
    from generate.binding_graph import (
        BoundEquation,
        SourceSpanLink,
        SymbolBinding,
        check_admissibility,
    )
    from generate.quantitative_expr import Mul

    span = SourceSpanLink(source_id="t", start=0, end=1, text="x")
    symbols = {
        "a": SymbolBinding(symbol_id="a", name="a", semantic_role="quantity",
                           source_span=span, introduced_by="t", entity="a", unit="item"),
        "b": SymbolBinding(symbol_id="b", name="b", semantic_role="quantity",
                           source_span=span, introduced_by="t", entity="b", unit="item"),
    }
    eq = BoundEquation(
        lhs_symbol_id="c", rhs_canonical="a * b", operation_kind="multiply",
        dependencies=frozenset({"a", "b"}), unit_proof="placeholder",
        admissibility_status="pending", source_span=span,
    )
    # The dimensional checker ADMITS count×count (→ item²) — it does not refuse it.
    proof = check_admissibility(eq, symbols=symbols)
    assert proof.operation_kind == "multiply"
    # But the projection REFUSES the same shape — the boundary that keeps wrong=0.
    assert to_relation("c", Mul(Symbol("a"), Symbol("b"))) is None


# --------------------------------------------------------------------------- #
# PR-6c — the divisive comparative (Div), the divisor twin of Mul
# --------------------------------------------------------------------------- #


def test_div_serialization_and_derivations() -> None:
    from generate.quantitative_expr import Div

    d = Div(Symbol("carl"), Literal(2))
    assert to_canonical_string(d) == "carl / 2"
    assert dependencies(d) == frozenset({"carl"})  # the literal divisor is NOT a dep
    assert operation_kind(d) == "divide"
    assert to_relation("dora", d) == {
        "kind": "divide_by", "entity": "dora", "ref": "carl", "divisor": 2,
    }


def test_div_projection_admits_only_symbol_over_literal() -> None:
    """``Div(Symbol, Literal)`` is the ONLY shape that projects to ``divide_by``; every
    other ``Div`` shape REFUSES (``to_relation`` → None) — the divisor-only twin of the
    scalar-only Mul contract.

    Meaningful-fail: a ``Div(Symbol, Symbol)`` is a quantity-over-quantity ratio (the
    rate-divide family), NOT a divide-by-dimensionless-literal; projecting it as
    ``divide_by`` would fabricate a divisor. These asserts fail the moment that guard is
    loosened.
    """
    from generate.quantitative_expr import Div

    # The one admitted shape.
    assert to_relation("dora", Div(Symbol("carl"), Literal(2))) == {
        "kind": "divide_by", "entity": "dora", "ref": "carl", "divisor": 2,
    }
    # Quantity over quantity (a ratio), not a dimensionless divide → refuse.
    assert to_relation("dora", Div(Symbol("a"), Symbol("b"))) is None
    # Commuted (literal dividend) → refuse.
    assert to_relation("dora", Div(Literal(8), Symbol("a"))) is None
    # Compound divisor → refuse.
    assert to_relation("dora", Div(Symbol("a"), Add(Symbol("b"), Literal(1)))) is None
    # A bare literal quotient carries no symbol to reference → refuse.
    assert to_relation("dora", Div(Literal(8), Literal(2))) is None


def test_div_is_symmetric_with_mul_in_the_ir() -> None:
    """``Div`` and ``Mul`` are structural twins: single-symbol dep, dimensionless literal
    operand, the operand is never a dependency. This symmetry is what lets the reader
    build BOTH uniformly (``deps = dependencies(expr)``) without a per-op special case.
    """
    from generate.quantitative_expr import Div, Mul

    mul = Mul(Symbol("anna"), Literal(2))
    div = Div(Symbol("carl"), Literal(2))
    assert dependencies(mul) == frozenset({"anna"})
    assert dependencies(div) == frozenset({"carl"})  # identical shape: literal not a dep
    assert operation_kind(mul) == "multiply"
    assert operation_kind(div) == "divide"
