"""ADR-0132 — Tests for the Semantic-Symbolic Binding Graph data model.

Covers:
  - frozen / slots invariants (no field mutation, no attribute injection),
  - construction-time refusals (typed BindingGraphError),
  - cross-collection invariants on SemanticSymbolicBindingGraph,
  - allocation determinism (byte-equal under replay),
  - canonical string round-trip / stability.

Pure data layer — no runtime, no parser, no algebra imports.
"""

from __future__ import annotations

import dataclasses

import pytest

from generate.binding_graph import (
    ADMISSIBILITY_STATUSES,
    SEMANTIC_ROLES,
    BindingGraphError,
    BoundConstraint,
    BoundEquation,
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
    allocate_symbols,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _span(
    *, source_id: str = "src1", start: int = 0, end: int = 5, text: str = "hello"
) -> SourceSpanLink:
    return SourceSpanLink(source_id=source_id, start=start, end=end, text=text)


def _sym(
    symbol_id: str = "sym_x_000",
    *,
    name: str = "x",
    role: str = "quantity",
    entity: str | None = None,
    unit: str | None = None,
) -> SymbolBinding:
    return SymbolBinding(
        symbol_id=symbol_id,
        name=name,
        semantic_role=role,
        source_span=_span(),
        introduced_by="test",
        entity=entity,
        unit=unit,
    )


# ---------------------------------------------------------------------------
# Closed-vocabulary contracts
# ---------------------------------------------------------------------------


def test_semantic_roles_is_frozenset_and_closed() -> None:
    assert isinstance(SEMANTIC_ROLES, frozenset)
    assert "quantity" in SEMANTIC_ROLES
    assert "unknown" in SEMANTIC_ROLES
    # Closed vocabulary — adding new roles is a deliberate ADR change.
    assert SEMANTIC_ROLES == {
        "entity", "quantity", "rate", "duration", "count",
        "total", "difference", "ratio", "unknown",
    }


def test_admissibility_statuses_closed_set() -> None:
    assert ADMISSIBILITY_STATUSES == {"admitted", "pending", "refused"}


# ---------------------------------------------------------------------------
# SourceSpanLink
# ---------------------------------------------------------------------------


def test_source_span_link_basic_construction() -> None:
    span = SourceSpanLink(source_id="doc", start=3, end=8, text="apple")
    assert span.text == "apple"
    assert span.to_canonical_string() == "doc[3:8]"


def test_source_span_link_is_frozen() -> None:
    span = _span()
    with pytest.raises(dataclasses.FrozenInstanceError):
        span.start = 99  # type: ignore[misc]


def test_source_span_link_refuses_empty_text() -> None:
    with pytest.raises(BindingGraphError):
        SourceSpanLink(source_id="doc", start=0, end=4, text="")


def test_source_span_link_refuses_empty_source_id() -> None:
    with pytest.raises(BindingGraphError):
        SourceSpanLink(source_id="", start=0, end=4, text="hi")


def test_source_span_link_refuses_negative_start() -> None:
    with pytest.raises(BindingGraphError):
        SourceSpanLink(source_id="d", start=-1, end=4, text="hi")


def test_source_span_link_refuses_end_le_start() -> None:
    with pytest.raises(BindingGraphError):
        SourceSpanLink(source_id="d", start=5, end=5, text="hi")
    with pytest.raises(BindingGraphError):
        SourceSpanLink(source_id="d", start=5, end=2, text="hi")


def test_source_span_link_refuses_bool_start() -> None:
    # bool is a subclass of int — must refuse explicitly.
    with pytest.raises(BindingGraphError):
        SourceSpanLink(source_id="d", start=True, end=4, text="hi")  # type: ignore[arg-type]


def test_source_span_link_equality_and_hash() -> None:
    a = _span()
    b = _span()
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


# ---------------------------------------------------------------------------
# SymbolBinding
# ---------------------------------------------------------------------------


def test_symbol_binding_basic_construction() -> None:
    sym = _sym()
    assert sym.symbol_id == "sym_x_000"
    assert sym.entity is None
    assert sym.unit is None


def test_symbol_binding_is_frozen() -> None:
    sym = _sym()
    with pytest.raises(dataclasses.FrozenInstanceError):
        sym.name = "y"  # type: ignore[misc]


def test_symbol_binding_uses_slots() -> None:
    sym = _sym()
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError, TypeError)):
        sym.extra = "nope"  # type: ignore[attr-defined]


def test_symbol_binding_refuses_non_identifier_symbol_id() -> None:
    with pytest.raises(BindingGraphError):
        _sym(symbol_id="not an identifier")


def test_symbol_binding_refuses_empty_symbol_id() -> None:
    with pytest.raises(BindingGraphError):
        _sym(symbol_id="")


def test_symbol_binding_refuses_unknown_role() -> None:
    with pytest.raises(BindingGraphError):
        _sym(role="velocity")


@pytest.mark.parametrize("role", sorted(SEMANTIC_ROLES))
def test_symbol_binding_accepts_every_documented_role(role: str) -> None:
    sym = _sym(role=role)
    assert sym.semantic_role == role


def test_symbol_binding_refuses_non_span_source() -> None:
    with pytest.raises(BindingGraphError):
        SymbolBinding(
            symbol_id="x",
            name="x",
            semantic_role="quantity",
            source_span="not-a-span",  # type: ignore[arg-type]
            introduced_by="t",
        )


def test_symbol_binding_optional_entity_unit() -> None:
    sym = _sym(entity="Tina", unit="dollars/hour")
    assert sym.entity == "Tina"
    assert sym.unit == "dollars/hour"


def test_symbol_binding_refuses_empty_unit_string() -> None:
    with pytest.raises(BindingGraphError):
        _sym(unit="")


# ---------------------------------------------------------------------------
# BoundFact
# ---------------------------------------------------------------------------


def test_bound_fact_construction_and_frozen() -> None:
    fact = BoundFact(
        symbol_id="sym_x_000", value="5", source_span=_span(), unit="apples"
    )
    assert fact.value == "5"
    with pytest.raises(dataclasses.FrozenInstanceError):
        fact.value = "6"  # type: ignore[misc]


def test_bound_fact_refuses_non_identifier_symbol_id() -> None:
    with pytest.raises(BindingGraphError):
        BoundFact(symbol_id="not id", value="5", source_span=_span())


def test_bound_fact_refuses_empty_value() -> None:
    with pytest.raises(BindingGraphError):
        BoundFact(symbol_id="sym_x_000", value="", source_span=_span())


# ---------------------------------------------------------------------------
# BoundEquation
# ---------------------------------------------------------------------------


def _eq(**overrides: object) -> BoundEquation:
    defaults: dict[str, object] = dict(
        lhs_symbol_id="sym_y_000",
        rhs_canonical="sym_x_000+1",
        dependencies=frozenset({"sym_x_000"}),
        operation_kind="affine",
        unit_proof="apples == apples",
        admissibility_status="admitted",
        source_span=_span(),
    )
    defaults.update(overrides)
    return BoundEquation(**defaults)  # type: ignore[arg-type]


def test_bound_equation_admitted_basic() -> None:
    eq = _eq()
    assert eq.refusal_reason is None
    assert "sym_x_000" in eq.dependencies


def test_bound_equation_refused_requires_reason() -> None:
    with pytest.raises(BindingGraphError):
        _eq(admissibility_status="refused")


def test_bound_equation_refused_with_reason_ok() -> None:
    eq = _eq(admissibility_status="refused", refusal_reason="unit mismatch")
    assert eq.refusal_reason == "unit mismatch"


def test_bound_equation_non_refused_must_have_no_reason() -> None:
    with pytest.raises(BindingGraphError):
        _eq(admissibility_status="admitted", refusal_reason="nope")


def test_bound_equation_refuses_bad_status() -> None:
    with pytest.raises(BindingGraphError):
        _eq(admissibility_status="approved")


def test_bound_equation_refuses_mutable_dependency_set() -> None:
    with pytest.raises(BindingGraphError):
        _eq(dependencies={"sym_x_000"})  # type: ignore[arg-type]


def test_bound_equation_refuses_non_identifier_dependency() -> None:
    with pytest.raises(BindingGraphError):
        _eq(dependencies=frozenset({"bad id"}))


def test_bound_equation_refuses_non_identifier_lhs() -> None:
    with pytest.raises(BindingGraphError):
        _eq(lhs_symbol_id="bad lhs")


def test_bound_equation_is_frozen() -> None:
    eq = _eq()
    with pytest.raises(dataclasses.FrozenInstanceError):
        eq.rhs_canonical = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BoundUnknown
# ---------------------------------------------------------------------------


def test_bound_unknown_construction() -> None:
    unk = BoundUnknown(
        symbol_id="sym_y_000",
        question_span=_span(),
        state_index="terminal",
        question_form="count",
        expected_unit="dollars",
    )
    assert unk.expected_unit == "dollars"


def test_bound_unknown_refuses_bad_id() -> None:
    with pytest.raises(BindingGraphError):
        BoundUnknown(
            symbol_id="bad id",
            question_span=_span(),
            state_index="terminal",
            question_form="count",
        )


def test_bound_unknown_refuses_non_span_question() -> None:
    with pytest.raises(BindingGraphError):
        BoundUnknown(
            symbol_id="sym_y_000",
            question_span="text",  # type: ignore[arg-type]
            state_index="terminal",
            question_form="count",
        )


# ---------------------------------------------------------------------------
# BoundConstraint
# ---------------------------------------------------------------------------


def test_bound_constraint_construction() -> None:
    con = BoundConstraint(
        symbol_id="sym_x_000", predicate="x >= 0", source_span=_span()
    )
    assert con.predicate == "x >= 0"


def test_bound_constraint_refuses_empty_predicate() -> None:
    with pytest.raises(BindingGraphError):
        BoundConstraint(
            symbol_id="sym_x_000", predicate="", source_span=_span()
        )


# ---------------------------------------------------------------------------
# SemanticSymbolicBindingGraph
# ---------------------------------------------------------------------------


def test_graph_empty_construction() -> None:
    g = SemanticSymbolicBindingGraph()
    assert g.symbols == ()
    assert g.facts == ()
    assert g.equations == ()
    assert g.unknowns == ()
    assert g.constraints == ()
    assert g.provenance == ()


def test_graph_rejects_list_for_symbols() -> None:
    with pytest.raises(BindingGraphError):
        SemanticSymbolicBindingGraph(symbols=[_sym()])  # type: ignore[arg-type]


def test_graph_rejects_duplicate_symbol_id() -> None:
    a = _sym("sym_x_000")
    b = _sym("sym_x_000")
    with pytest.raises(BindingGraphError):
        SemanticSymbolicBindingGraph(symbols=(a, b))


def test_graph_rejects_fact_referencing_unknown_symbol() -> None:
    fact = BoundFact(symbol_id="sym_ghost_000", value="1", source_span=_span())
    with pytest.raises(BindingGraphError):
        SemanticSymbolicBindingGraph(symbols=(_sym(),), facts=(fact,))


def test_graph_rejects_equation_referencing_unknown_lhs() -> None:
    eq = _eq(lhs_symbol_id="sym_ghost_000")
    with pytest.raises(BindingGraphError):
        SemanticSymbolicBindingGraph(symbols=(_sym(),), equations=(eq,))


def test_graph_rejects_equation_with_unknown_dependency() -> None:
    eq = _eq(dependencies=frozenset({"sym_ghost_000"}))
    with pytest.raises(BindingGraphError):
        SemanticSymbolicBindingGraph(
            symbols=(_sym("sym_y_000"),), equations=(eq,)
        )


def test_graph_rejects_unknown_referencing_missing_symbol() -> None:
    unk = BoundUnknown(
        symbol_id="sym_ghost_000",
        question_span=_span(),
        state_index="terminal",
        question_form="count",
    )
    with pytest.raises(BindingGraphError):
        SemanticSymbolicBindingGraph(symbols=(_sym(),), unknowns=(unk,))


def test_graph_rejects_constraint_referencing_missing_symbol() -> None:
    con = BoundConstraint(
        symbol_id="sym_ghost_000", predicate="x >= 0", source_span=_span()
    )
    with pytest.raises(BindingGraphError):
        SemanticSymbolicBindingGraph(symbols=(_sym(),), constraints=(con,))


def test_graph_full_round_trip_canonical_string_stable() -> None:
    syms = (
        _sym("sym_x_000", name="x"),
        _sym("sym_y_000", name="y", role="unknown"),
    )
    facts = (
        BoundFact(symbol_id="sym_x_000", value="5", source_span=_span(), unit="apples"),
    )
    eqs = (_eq(),)
    unks = (
        BoundUnknown(
            symbol_id="sym_y_000",
            question_span=_span(),
            state_index="terminal",
            question_form="count",
        ),
    )
    cons = (
        BoundConstraint(symbol_id="sym_x_000", predicate="x >= 0", source_span=_span()),
    )
    g1 = SemanticSymbolicBindingGraph(
        symbols=syms, facts=facts, equations=eqs, unknowns=unks, constraints=cons
    )
    g2 = SemanticSymbolicBindingGraph(
        symbols=syms, facts=facts, equations=eqs, unknowns=unks, constraints=cons
    )
    assert g1.to_canonical_string() == g2.to_canonical_string()
    assert g1 == g2


def test_graph_is_frozen() -> None:
    g = SemanticSymbolicBindingGraph()
    with pytest.raises(dataclasses.FrozenInstanceError):
        g.symbols = (_sym(),)  # type: ignore[misc]


def test_graph_canonical_string_order_sensitive() -> None:
    a = _sym("sym_a_000", name="a")
    b = _sym("sym_b_000", name="b")
    g_ab = SemanticSymbolicBindingGraph(symbols=(a, b))
    g_ba = SemanticSymbolicBindingGraph(symbols=(b, a))
    # Caller controls order — identity-preserving by design.
    assert g_ab.to_canonical_string() != g_ba.to_canonical_string()


# ---------------------------------------------------------------------------
# allocate_symbols — determinism
# ---------------------------------------------------------------------------


def test_allocate_symbols_basic() -> None:
    span = _span()
    out = allocate_symbols(
        ("Tina", "wage", "hours"), source_span=span, introduced_by="parser_v1"
    )
    assert len(out) == 3
    assert tuple(s.symbol_id for s in out) == (
        "sym_tina_000", "sym_wage_001", "sym_hours_002",
    )
    assert all(isinstance(s, SymbolBinding) for s in out)
    assert out[0].source_span == span


def test_allocate_symbols_is_deterministic_across_calls() -> None:
    span = _span()
    a = allocate_symbols(
        ("alpha", "beta", "gamma"), source_span=span, introduced_by="t"
    )
    b = allocate_symbols(
        ("alpha", "beta", "gamma"), source_span=span, introduced_by="t"
    )
    assert a == b
    assert tuple(s.symbol_id for s in a) == tuple(s.symbol_id for s in b)


def test_allocate_symbols_disambiguates_collisions_by_index() -> None:
    out = allocate_symbols(
        ("price", "Price", "PRICE"),
        source_span=_span(),
        introduced_by="t",
    )
    ids = tuple(s.symbol_id for s in out)
    assert ids == ("sym_price_000", "sym_price_001", "sym_price_002")
    assert len(set(ids)) == 3


def test_allocate_symbols_slugifies_non_ascii_whitespace() -> None:
    out = allocate_symbols(
        ("dollars per hour", "  spaced  "),
        source_span=_span(),
        introduced_by="t",
    )
    assert out[0].symbol_id == "sym_dollars_per_hour_000"
    assert out[1].symbol_id == "sym_spaced_001"
    assert out[1].name == "spaced"


def test_allocate_symbols_refuses_empty_iterable() -> None:
    with pytest.raises(BindingGraphError):
        allocate_symbols((), source_span=_span(), introduced_by="t")


def test_allocate_symbols_refuses_empty_phrase() -> None:
    with pytest.raises(BindingGraphError):
        allocate_symbols(
            ("ok", "   "), source_span=_span(), introduced_by="t"
        )


def test_allocate_symbols_refuses_unslugifiable_phrase() -> None:
    with pytest.raises(BindingGraphError):
        allocate_symbols(
            ("ok", "!!!"), source_span=_span(), introduced_by="t"
        )


def test_allocate_symbols_refuses_unknown_role() -> None:
    with pytest.raises(BindingGraphError):
        allocate_symbols(
            ("x",),
            source_span=_span(),
            introduced_by="t",
            semantic_role="velocity",
        )


def test_allocate_symbols_refuses_bad_prefix() -> None:
    with pytest.raises(BindingGraphError):
        allocate_symbols(
            ("x",),
            source_span=_span(),
            introduced_by="t",
            prefix="not id",
        )


def test_allocate_symbols_refuses_empty_introduced_by() -> None:
    with pytest.raises(BindingGraphError):
        allocate_symbols(("x",), source_span=_span(), introduced_by="")


def test_allocate_symbols_role_threaded_through() -> None:
    out = allocate_symbols(
        ("earnings",),
        source_span=_span(),
        introduced_by="t",
        semantic_role="total",
    )
    assert out[0].semantic_role == "total"


def test_allocate_symbols_into_graph_round_trip() -> None:
    syms = allocate_symbols(
        ("apples", "oranges"), source_span=_span(), introduced_by="t"
    )
    g = SemanticSymbolicBindingGraph(symbols=syms)
    # Round trip through canonical string twice must be byte-equal.
    s1 = g.to_canonical_string()
    s2 = SemanticSymbolicBindingGraph(symbols=syms).to_canonical_string()
    assert s1 == s2


def test_allocate_symbols_returns_tuple() -> None:
    out = allocate_symbols(("x",), source_span=_span(), introduced_by="t")
    assert isinstance(out, tuple)
