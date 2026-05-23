"""ADR-0133 — Tests for the MathProblemGraph → BindingGraph adapter.

Covers:
  - refusal-first on malformed input (typed ``AdapterError``),
  - per-operation-kind round-trip (string passthrough on the closed vocab),
  - entity / quantity / unknown mapping discipline,
  - deterministic introduction-order preservation,
  - dependency wiring against pre-existing t0 symbols,
  - byte-equal idempotency across runs (hash-stability),
  - input immutability and frozen-output invariants,
  - Phase-2 placeholders for ``unit_proof`` + admissibility (Phase 3+ deferred).

Pure data — no runtime, no algebra, no parser imports.
"""

from __future__ import annotations

import dataclasses

import pytest

from generate.binding_graph import (
    INTRODUCED_BY,
    REFUSED_UNIT_PROOF,
    SYNTHETIC_SOURCE_ID,
    AdapterError,
    BoundEquation,
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SymbolBinding,
    bind_math_problem_graph,
)
from generate.math_problem_graph import (
    VALID_OPERATION_KINDS,
    Comparison,
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
    Rate,
    Unknown,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _q(value: int | float, unit: str) -> Quantity:
    return Quantity(value=value, unit=unit)


def _trivial_graph() -> MathProblemGraph:
    return MathProblemGraph(
        entities=("Sam",),
        initial_state=(InitialPossession(entity="Sam", quantity=_q(3, "apples")),),
        operations=(),
        unknown=Unknown(entity="Sam", unit="apples"),
    )


def _two_actor_add_graph() -> MathProblemGraph:
    return MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "apples")),
            InitialPossession(entity="Mary", quantity=_q(5, "apples")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(2, "apples")),
        ),
        unknown=Unknown(entity=None, unit="apples"),
    )


def _transfer_graph() -> MathProblemGraph:
    return MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(7, "apples")),
            InitialPossession(entity="Mary", quantity=_q(1, "apples")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="transfer",
                operand=_q(3, "apples"),
                target="Mary",
            ),
        ),
        unknown=Unknown(entity="Mary", unit="apples"),
    )


def _rate_graph() -> MathProblemGraph:
    return MathProblemGraph(
        entities=("Sam",),
        initial_state=(InitialPossession(entity="Sam", quantity=_q(4, "apple")),),
        operations=(
            Operation(
                actor="Sam",
                kind="apply_rate",
                operand=Rate(
                    value=2.0, numerator_unit="dollars", denominator_unit="apple"
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="dollars"),
    )


def _compare_additive_graph() -> MathProblemGraph:
    return MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Mary", quantity=_q(5, "apples")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="compare_additive",
                operand=Comparison(
                    reference_actor="Mary",
                    delta=_q(2, "apples"),
                    factor=None,
                    direction="more",
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="apples"),
    )


def _compare_multiplicative_graph() -> MathProblemGraph:
    return MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Mary", quantity=_q(5, "apples")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="compare_multiplicative",
                operand=Comparison(
                    reference_actor="Mary",
                    delta=None,
                    factor=3.0,
                    direction="times",
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="apples"),
    )


# ---------------------------------------------------------------------------
# 1-3. Refusal-first on malformed input
# ---------------------------------------------------------------------------


def test_adapter_refuses_non_graph_input() -> None:
    with pytest.raises(AdapterError):
        bind_math_problem_graph({"entities": ()})  # type: ignore[arg-type]


def test_adapter_refuses_none() -> None:
    with pytest.raises(AdapterError):
        bind_math_problem_graph(None)  # type: ignore[arg-type]


def test_adapter_refuses_string() -> None:
    with pytest.raises(AdapterError):
        bind_math_problem_graph("not a graph")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 4-7. Minimal-graph shape
# ---------------------------------------------------------------------------


def test_trivial_graph_emits_expected_symbol_count() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    # 1 entity + 1 initial-quantity + 1 unknown synthesis
    assert len(bg.symbols) == 3
    assert len(bg.facts) == 1
    assert len(bg.equations) == 0
    assert len(bg.unknowns) == 1


def test_entity_symbol_has_entity_role_and_slug() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    entity_syms = [s for s in bg.symbols if s.semantic_role == "entity"]
    assert len(entity_syms) == 1
    assert entity_syms[0].symbol_id == "entity_sam"
    assert entity_syms[0].name == "Sam"
    assert entity_syms[0].entity == "Sam"


def test_initial_possession_emits_fact_with_str_value_and_unit() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    fact = bg.facts[0]
    assert fact.symbol_id == "q_sam_apples_t0"
    assert fact.value == "3"
    assert fact.unit == "apples"


def test_initial_quantity_symbol_has_quantity_role_and_unit() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    quant_syms = [
        s
        for s in bg.symbols
        if s.semantic_role == "quantity" and s.symbol_id.startswith("q_")
    ]
    assert len(quant_syms) == 1
    assert quant_syms[0].unit == "apples"
    assert quant_syms[0].entity == "Sam"


# ---------------------------------------------------------------------------
# 8-9. Unknown handling
# ---------------------------------------------------------------------------


def test_unknown_bound_to_synthesized_symbol() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    unk = bg.unknowns[0]
    syms_by_id = {s.symbol_id: s for s in bg.symbols}
    assert unk.symbol_id in syms_by_id
    assert syms_by_id[unk.symbol_id].semantic_role == "unknown"
    assert unk.expected_unit == "apples"


def test_unknown_entity_none_renders_total_scope() -> None:
    bg = bind_math_problem_graph(_two_actor_add_graph())
    unk = bg.unknowns[0]
    assert unk.symbol_id == "unknown_total_apples"


# ---------------------------------------------------------------------------
# 10-17. Per-operation-kind passthrough (covers all 8 in VALID_OPERATION_KINDS)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind,operand,target",
    [
        ("add", _q(2, "apples"), None),
        ("subtract", _q(2, "apples"), None),
        ("multiply", _q(2, "apples"), None),
        ("divide", _q(2, "apples"), None),
    ],
)
def test_simple_operation_kind_passthrough(
    kind: str, operand: Quantity, target: str | None
) -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(10, "apples")),
        ),
        operations=(Operation(actor="Sam", kind=kind, operand=operand, target=target),),
        unknown=Unknown(entity="Sam", unit="apples"),
    )
    bg = bind_math_problem_graph(g)
    assert len(bg.equations) == 1
    assert bg.equations[0].operation_kind == kind
    # passthrough must match the source closed vocab verbatim
    assert bg.equations[0].operation_kind in VALID_OPERATION_KINDS


def test_transfer_passthrough_and_dep_on_both_actors() -> None:
    bg = bind_math_problem_graph(_transfer_graph())
    eq = bg.equations[0]
    assert eq.operation_kind == "transfer"
    assert "q_sam_apples_t0" in eq.dependencies
    assert "q_mary_apples_t0" in eq.dependencies


def test_apply_rate_passthrough_and_dep_on_denominator_unit() -> None:
    bg = bind_math_problem_graph(_rate_graph())
    eq = bg.equations[0]
    assert eq.operation_kind == "apply_rate"
    # Sam holds 'apple' (denominator); dep wires there.
    assert "q_sam_apple_t0" in eq.dependencies


def test_compare_additive_passthrough_and_dep_on_reference() -> None:
    bg = bind_math_problem_graph(_compare_additive_graph())
    eq = bg.equations[0]
    assert eq.operation_kind == "compare_additive"
    assert "q_mary_apples_t0" in eq.dependencies


def test_compare_multiplicative_passthrough() -> None:
    bg = bind_math_problem_graph(_compare_multiplicative_graph())
    eq = bg.equations[0]
    assert eq.operation_kind == "compare_multiplicative"
    # multiplicative comparison has no delta-unit → no t0 dep wired
    assert eq.dependencies == frozenset()


def test_all_eight_operation_kinds_round_trip() -> None:
    # Sanity: brief mandates the closed vocab is shared by design.
    # Each kind exercised individually above; here we just assert the
    # vocab itself hasn't drifted under us.
    assert VALID_OPERATION_KINDS == frozenset(
        {
            "add",
            "subtract",
            "transfer",
            "multiply",
            "divide",
            "apply_rate",
            "compare_additive",
            "compare_multiplicative",
        }
    )


# ---------------------------------------------------------------------------
# 18-22. Determinism, immutability, hash-stability
# ---------------------------------------------------------------------------


def test_adapter_is_idempotent_on_equal_graphs() -> None:
    a = bind_math_problem_graph(_two_actor_add_graph())
    b = bind_math_problem_graph(_two_actor_add_graph())
    assert a == b
    assert a.to_canonical_string() == b.to_canonical_string()


def test_canonical_string_is_byte_equal_across_runs() -> None:
    g = _transfer_graph()
    s1 = bind_math_problem_graph(g).to_canonical_string()
    s2 = bind_math_problem_graph(g).to_canonical_string()
    assert s1.encode("utf-8") == s2.encode("utf-8")


def test_introduction_order_preserved_across_entities() -> None:
    g = MathProblemGraph(
        entities=("Zeta", "Alpha", "Mu"),
        initial_state=(),
        operations=(),
        unknown=Unknown(entity="Alpha", unit="widgets"),
    )
    bg = bind_math_problem_graph(g)
    entity_syms = [s for s in bg.symbols if s.semantic_role == "entity"]
    assert [s.name for s in entity_syms] == ["Zeta", "Alpha", "Mu"]


def test_input_graph_not_mutated() -> None:
    g = _transfer_graph()
    entities_before = g.entities
    ops_before = g.operations
    bind_math_problem_graph(g)
    # Frozen + slots makes mutation impossible; assert object identity
    # of the immutable tuples as a defense-in-depth contract.
    assert g.entities is entities_before
    assert g.operations is ops_before


def test_output_dataclasses_are_frozen() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    sym = bg.symbols[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        sym.name = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 23-26. Phase-2 placeholders + cross-collection invariants
# ---------------------------------------------------------------------------


def test_phase3_refused_equations_carry_typed_refusal() -> None:
    # ADR-0134: 'apples' is not in en_units_v1 → typed refusal, never silent.
    bg = bind_math_problem_graph(_two_actor_add_graph())
    eq = bg.equations[0]
    assert eq.admissibility_status == "refused"
    assert eq.refusal_reason == "unknown_unit"
    assert eq.unit_proof == REFUSED_UNIT_PROOF


def test_phase3_admitted_equations_carry_populated_unit_proof() -> None:
    # Build a fully-grounded analog in the closed unit vocabulary.
    g = MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Sam", quantity=Quantity(value=3, unit="dollar")),
            InitialPossession(entity="Mary", quantity=Quantity(value=4, unit="dollar")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=Quantity(value=2, unit="dollar")),
        ),
        unknown=Unknown(entity=None, unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    eq = bg.equations[0]
    assert eq.admissibility_status == "admitted"
    assert eq.refusal_reason is None
    assert eq.unit_proof != REFUSED_UNIT_PROOF
    assert eq.unit_proof.startswith("add:")


def test_all_equation_dependencies_reference_known_symbols() -> None:
    bg = bind_math_problem_graph(_transfer_graph())
    known = {s.symbol_id for s in bg.symbols}
    for eq in bg.equations:
        assert eq.dependencies.issubset(known)


def test_unknown_symbol_id_references_known_symbol() -> None:
    bg = bind_math_problem_graph(_compare_additive_graph())
    known = {s.symbol_id for s in bg.symbols}
    assert bg.unknowns[0].symbol_id in known


# ---------------------------------------------------------------------------
# 27-31. Provenance + constants
# ---------------------------------------------------------------------------


def test_every_symbol_introduced_by_constant() -> None:
    bg = bind_math_problem_graph(_transfer_graph())
    for sym in bg.symbols:
        assert sym.introduced_by == INTRODUCED_BY


def test_synthetic_source_id_on_every_span() -> None:
    bg = bind_math_problem_graph(_transfer_graph())
    for sym in bg.symbols:
        assert sym.source_span.source_id == SYNTHETIC_SOURCE_ID
    for fact in bg.facts:
        assert fact.source_span.source_id == SYNTHETIC_SOURCE_ID
    for eq in bg.equations:
        assert eq.source_span.source_id == SYNTHETIC_SOURCE_ID
    for unk in bg.unknowns:
        assert unk.question_span.source_id == SYNTHETIC_SOURCE_ID


def test_op_result_symbol_id_is_deterministic_and_indexed() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(InitialPossession(entity="Sam", quantity=_q(1, "u")),),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(1, "u")),
            Operation(actor="Sam", kind="add", operand=_q(2, "u")),
            Operation(actor="Sam", kind="add", operand=_q(3, "u")),
        ),
        unknown=Unknown(entity="Sam", unit="u"),
    )
    bg = bind_math_problem_graph(g)
    lhs = [eq.lhs_symbol_id for eq in bg.equations]
    assert lhs == ["op_000_result", "op_001_result", "op_002_result"]


def test_rhs_canonical_contains_operation_kind() -> None:
    bg = bind_math_problem_graph(_transfer_graph())
    assert bg.equations[0].rhs_canonical.startswith("transfer(")


def test_bound_unknown_is_single_target() -> None:
    bg = bind_math_problem_graph(_compare_multiplicative_graph())
    # Phase 2 promise: exactly one unknown binding per graph.
    assert len(bg.unknowns) == 1
    assert isinstance(bg.unknowns[0], BoundUnknown)


# ---------------------------------------------------------------------------
# 32-34. Misc edge cases
# ---------------------------------------------------------------------------


def test_graph_with_zero_operations_is_well_formed() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    assert bg.equations == ()
    # round-trip stays valid under SemanticSymbolicBindingGraph invariants
    assert isinstance(bg, SemanticSymbolicBindingGraph)


def test_entity_with_spaces_slugifies_into_valid_identifier() -> None:
    g = MathProblemGraph(
        entities=("Mary Jane",),
        initial_state=(
            InitialPossession(entity="Mary Jane", quantity=_q(2, "apples")),
        ),
        operations=(),
        unknown=Unknown(entity="Mary Jane", unit="apples"),
    )
    bg = bind_math_problem_graph(g)
    entity_syms = [s for s in bg.symbols if s.semantic_role == "entity"]
    assert entity_syms[0].symbol_id == "entity_mary_jane"
    assert entity_syms[0].symbol_id.isidentifier()


def test_fact_count_matches_initial_possession_count() -> None:
    bg = bind_math_problem_graph(_two_actor_add_graph())
    assert len(bg.facts) == 2


def test_outputs_for_distinct_graphs_differ() -> None:
    s1 = bind_math_problem_graph(_trivial_graph()).to_canonical_string()
    s2 = bind_math_problem_graph(_transfer_graph()).to_canonical_string()
    assert s1 != s2


def test_symbol_table_has_no_duplicate_ids() -> None:
    bg = bind_math_problem_graph(_transfer_graph())
    ids = [s.symbol_id for s in bg.symbols]
    assert len(ids) == len(set(ids))


def test_equation_lhs_is_a_known_symbol() -> None:
    bg = bind_math_problem_graph(_two_actor_add_graph())
    known = {s.symbol_id for s in bg.symbols}
    for eq in bg.equations:
        assert eq.lhs_symbol_id in known


def test_typeof_emitted_equation_is_bound_equation() -> None:
    bg = bind_math_problem_graph(_two_actor_add_graph())
    assert all(isinstance(eq, BoundEquation) for eq in bg.equations)


def test_typeof_emitted_fact_is_bound_fact() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    assert all(isinstance(f, BoundFact) for f in bg.facts)


def test_typeof_emitted_symbol_is_symbol_binding() -> None:
    bg = bind_math_problem_graph(_trivial_graph())
    assert all(isinstance(s, SymbolBinding) for s in bg.symbols)
