"""ADR-0134 — Equation admissibility check (per-kind dispatch).

Covers the closed eight-string ``operation_kind`` vocab with positive and
negative cases, plus the typed-refusal contract.
"""

from __future__ import annotations

import pytest

from generate.binding_graph import (
    ADMISSIBILITY_REASONS,
    AdmissibilityError,
    BoundEquation,
    SourceSpanLink,
    SymbolBinding,
    UnitProof,
    check_admissibility,
    parse_unit,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _span(text: str = "x") -> SourceSpanLink:
    return SourceSpanLink(source_id="t", start=0, end=len(text), text=text)


def _sym(
    sid: str,
    *,
    unit: str | None = None,
    role: str = "quantity",
) -> SymbolBinding:
    return SymbolBinding(
        symbol_id=sid,
        name=sid,
        semantic_role=role,
        source_span=_span(sid),
        introduced_by="test",
        unit=unit,
    )


def _eq(
    *,
    kind: str,
    deps: frozenset[str],
    lhs: str = "res",
) -> BoundEquation:
    return BoundEquation(
        lhs_symbol_id=lhs,
        rhs_canonical=f"{kind}(test)",
        dependencies=deps,
        operation_kind=kind,
        unit_proof="placeholder",
        admissibility_status="pending",
        source_span=_span(kind),
    )


# ---------------------------------------------------------------------------
# Closed refusal-reason vocab
# ---------------------------------------------------------------------------


def test_admissibility_reasons_is_closed_set() -> None:
    assert isinstance(ADMISSIBILITY_REASONS, frozenset)
    assert "unit_mismatch" in ADMISSIBILITY_REASONS
    assert "unknown_unit" in ADMISSIBILITY_REASONS
    assert "unit_unbound" in ADMISSIBILITY_REASONS
    assert "unknown_symbol" in ADMISSIBILITY_REASONS


def test_admissibility_error_rejects_unknown_reason() -> None:
    with pytest.raises(ValueError):
        AdmissibilityError("bogus", "x")


def test_admissibility_error_carries_typed_reason_and_detail() -> None:
    exc = AdmissibilityError("unit_mismatch", "sym_a != sym_b")
    assert exc.reason == "unit_mismatch"
    assert exc.detail == "sym_a != sym_b"


# ---------------------------------------------------------------------------
# add / subtract / compare_additive / transfer (additive class)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["add", "subtract", "compare_additive", "transfer"])
def test_additive_kinds_admit_matching_units(kind: str) -> None:
    symbols = {
        "a": _sym("a", unit="dollar"),
        "b": _sym("b", unit="dollar"),
    }
    proof = check_admissibility(
        _eq(kind=kind, deps=frozenset({"a", "b"})), symbols=symbols
    )
    assert isinstance(proof, UnitProof)
    assert proof.lhs_unit == parse_unit("dollar")
    assert proof.operation_kind == kind


@pytest.mark.parametrize("kind", ["add", "subtract", "compare_additive", "transfer"])
def test_additive_kinds_refuse_mismatched_units(kind: str) -> None:
    symbols = {
        "a": _sym("a", unit="dollar"),
        "b": _sym("b", unit="foot"),
    }
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind=kind, deps=frozenset({"a", "b"})), symbols=symbols
        )
    assert ei.value.reason == "unit_mismatch"


def test_add_admits_single_dep() -> None:
    # When the operand unit already matches the actor, a single-dep equation
    # is fine — verifier just records the unit.
    symbols = {"a": _sym("a", unit="dollar")}
    proof = check_admissibility(
        _eq(kind="add", deps=frozenset({"a"})), symbols=symbols
    )
    assert proof.lhs_unit == parse_unit("dollar")


def test_add_refuses_with_no_deps() -> None:
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(_eq(kind="add", deps=frozenset()), symbols={})
    assert ei.value.reason == "operand_arity"


def test_additive_refuses_three_way_unit_disagreement() -> None:
    symbols = {
        "a": _sym("a", unit="dollar"),
        "b": _sym("b", unit="dollar"),
        "c": _sym("c", unit="foot"),
    }
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="add", deps=frozenset({"a", "b", "c"})), symbols=symbols
        )
    assert ei.value.reason == "unit_mismatch"


# ---------------------------------------------------------------------------
# multiply
# ---------------------------------------------------------------------------


def test_multiply_lhs_is_product_of_dep_units() -> None:
    symbols = {
        "a": _sym("a", unit="foot"),
        "b": _sym("b", unit="foot"),
    }
    proof = check_admissibility(
        _eq(kind="multiply", deps=frozenset({"a", "b"})), symbols=symbols
    )
    assert proof.lhs_unit.exponents == (2, 0, 0, 0, 0, 0)


def test_multiply_mixed_units_yields_composite() -> None:
    symbols = {
        "a": _sym("a", unit="foot"),
        "b": _sym("b", unit="hour"),
    }
    proof = check_admissibility(
        _eq(kind="multiply", deps=frozenset({"a", "b"})), symbols=symbols
    )
    # length * time
    assert proof.lhs_unit.exponents == (1, 1, 0, 0, 0, 0)


def test_multiply_refuses_no_operands() -> None:
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="multiply", deps=frozenset()), symbols={}
        )
    assert ei.value.reason == "operand_arity"


def test_multiply_no_equality_requirement_between_operands() -> None:
    # Brief: "multiply / divide: lhs unit = product / quotient of operand
    # units; no equality requirement among operands."
    symbols = {
        "a": _sym("a", unit="foot"),
        "b": _sym("b", unit="pound"),
    }
    proof = check_admissibility(
        _eq(kind="multiply", deps=frozenset({"a", "b"})), symbols=symbols
    )
    # length * mass — no refusal, even though units differ.
    assert proof.lhs_unit.exponents == (1, 0, 1, 0, 0, 0)


# ---------------------------------------------------------------------------
# divide
# ---------------------------------------------------------------------------


def test_divide_lhs_is_quotient() -> None:
    symbols = {
        "q_actor_foot_t0": _sym("q_actor_foot_t0", unit="foot"),
        "op_000__divisor": _sym("op_000__divisor", unit="hour"),
    }
    proof = check_admissibility(
        _eq(
            kind="divide",
            deps=frozenset({"q_actor_foot_t0", "op_000__divisor"}),
        ),
        symbols=symbols,
    )
    # foot / hour = speed
    assert proof.lhs_unit.exponents == (1, -1, 0, 0, 0, 0)


def test_divide_refuses_when_no_divisor_named() -> None:
    symbols = {
        "a": _sym("a", unit="foot"),
        "b": _sym("b", unit="hour"),
    }
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="divide", deps=frozenset({"a", "b"})), symbols=symbols
        )
    assert ei.value.reason == "operand_arity"


def test_divide_refuses_three_deps() -> None:
    symbols = {
        "a": _sym("a", unit="foot"),
        "b": _sym("b", unit="hour"),
        "op_000__divisor": _sym("op_000__divisor", unit="hour"),
    }
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(
                kind="divide",
                deps=frozenset({"a", "b", "op_000__divisor"}),
            ),
            symbols=symbols,
        )
    assert ei.value.reason == "operand_arity"


# --------------------------------------------------------------------------- #
# ADR-0134 amendment 2026-06-07 — single-dep divide (divide by a dimensionless literal)
# --------------------------------------------------------------------------- #


def test_divide_single_dep_dimensionless_keeps_unit() -> None:
    """A single-dep divide (the reader's "half as many") divides by an implicit
    dimensionless literal and keeps the dividend's unit — symmetric with single-dep
    multiply.

    Meaningful-fail: if the ``len == 1`` branch were removed (reverting to ``!= 2``
    refuse), this admission turns into an ``operand_arity`` refusal and the assert fails.
    """
    symbols = {"carl": _sym("carl", unit="item")}
    proof = check_admissibility(
        _eq(kind="divide", deps=frozenset({"carl"})), symbols=symbols
    )
    assert proof.operation_kind == "divide"
    assert proof.lhs_unit == parse_unit("item")  # item / dimensionless = item
    assert proof.operand_units == (parse_unit("item"),)


def test_divide_refuses_zero_or_three_deps() -> None:
    """The single-dep extension is narrow: zero deps and three deps still refuse with
    ``operand_arity`` — only one (dimensionless divide) or two (rate divide) are admitted.
    """
    with pytest.raises(AdmissibilityError) as ei0:
        check_admissibility(_eq(kind="divide", deps=frozenset()), symbols={})
    assert ei0.value.reason == "operand_arity"

    symbols = {
        "a": _sym("a", unit="foot"),
        "b": _sym("b", unit="hour"),
        "op_000__divisor": _sym("op_000__divisor", unit="hour"),
    }
    with pytest.raises(AdmissibilityError) as ei3:
        check_admissibility(
            _eq(kind="divide", deps=frozenset({"a", "b", "op_000__divisor"})),
            symbols=symbols,
        )
    assert ei3.value.reason == "operand_arity"


def test_divide_two_dep_rate_path_unchanged_by_amendment() -> None:
    """The original two-dep rate divide (dividend + ``*__divisor``) is untouched — the
    amendment only ADDED the single-dep form."""
    symbols = {
        "q_actor_foot_t0": _sym("q_actor_foot_t0", unit="foot"),
        "op_000__divisor": _sym("op_000__divisor", unit="hour"),
    }
    proof = check_admissibility(
        _eq(kind="divide", deps=frozenset({"q_actor_foot_t0", "op_000__divisor"})),
        symbols=symbols,
    )
    assert proof.lhs_unit.exponents == (1, -1, 0, 0, 0, 0)  # foot / hour = speed


# ---------------------------------------------------------------------------
# apply_rate
# ---------------------------------------------------------------------------


def test_apply_rate_admits_clean_form() -> None:
    symbols = {
        "q_actor_hour_t0": _sym("q_actor_hour_t0", unit="hour"),
        "op_000__rate": _sym(
            "op_000__rate", unit="dollar_per_hour", role="rate"
        ),
    }
    proof = check_admissibility(
        _eq(
            kind="apply_rate",
            deps=frozenset({"q_actor_hour_t0", "op_000__rate"}),
        ),
        symbols=symbols,
    )
    # money/time × time = money
    assert proof.lhs_unit == parse_unit("dollar")


def test_apply_rate_refuses_when_duration_does_not_match_denominator() -> None:
    symbols = {
        "q_actor_foot_t0": _sym("q_actor_foot_t0", unit="foot"),
        "op_000__rate": _sym(
            "op_000__rate", unit="dollar_per_hour", role="rate"
        ),
    }
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(
                kind="apply_rate",
                deps=frozenset({"q_actor_foot_t0", "op_000__rate"}),
            ),
            symbols=symbols,
        )
    assert ei.value.reason == "rate_form_invalid"


def test_apply_rate_refuses_missing_rate_role() -> None:
    symbols = {
        "a": _sym("a", unit="hour"),
        "b": _sym("b", unit="dollar_per_hour"),  # role='quantity', not 'rate'
    }
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="apply_rate", deps=frozenset({"a", "b"})), symbols=symbols
        )
    assert ei.value.reason == "rate_form_invalid"


def test_apply_rate_refuses_wrong_arity() -> None:
    symbols = {
        "op_000__rate": _sym(
            "op_000__rate", unit="dollar_per_hour", role="rate"
        ),
    }
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="apply_rate", deps=frozenset({"op_000__rate"})),
            symbols=symbols,
        )
    assert ei.value.reason == "operand_arity"


# ---------------------------------------------------------------------------
# compare_multiplicative
# ---------------------------------------------------------------------------


def test_compare_multiplicative_lhs_is_dimensionless() -> None:
    symbols = {
        "a": _sym("a", unit="dollar"),
        "b": _sym("b", unit="dollar"),
    }
    proof = check_admissibility(
        _eq(kind="compare_multiplicative", deps=frozenset({"a", "b"})),
        symbols=symbols,
    )
    assert proof.lhs_unit.exponents == (0, 0, 0, 0, 0, 0)


def test_compare_multiplicative_no_deps_is_dimensionless() -> None:
    proof = check_admissibility(
        _eq(kind="compare_multiplicative", deps=frozenset()),
        symbols={},
    )
    assert proof.lhs_unit.exponents == (0, 0, 0, 0, 0, 0)


def test_compare_multiplicative_refuses_unit_mismatch() -> None:
    symbols = {
        "a": _sym("a", unit="dollar"),
        "b": _sym("b", unit="foot"),
    }
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="compare_multiplicative", deps=frozenset({"a", "b"})),
            symbols=symbols,
        )
    assert ei.value.reason == "unit_mismatch"


# ---------------------------------------------------------------------------
# Closed refusal-reason coverage
# ---------------------------------------------------------------------------


def test_refuses_unknown_symbol() -> None:
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="add", deps=frozenset({"missing"})), symbols={}
        )
    assert ei.value.reason == "unknown_symbol"
    assert ei.value.detail == "missing"


def test_refuses_unit_unbound_when_dep_symbol_has_no_unit() -> None:
    symbols = {"a": _sym("a", unit=None)}
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="add", deps=frozenset({"a"})), symbols=symbols
        )
    assert ei.value.reason == "unit_unbound"


def test_refuses_unknown_unit_when_dep_unit_outside_vocab() -> None:
    symbols = {"a": _sym("a", unit="apples")}
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(
            _eq(kind="add", deps=frozenset({"a"})), symbols=symbols
        )
    assert ei.value.reason == "unknown_unit"


def test_refuses_unknown_operation_kind() -> None:
    eq = _eq(kind="bogus_kind", deps=frozenset())
    with pytest.raises(AdmissibilityError) as ei:
        check_admissibility(eq, symbols={})
    assert ei.value.reason == "unknown_operation"


def test_check_admissibility_rejects_non_equation() -> None:
    with pytest.raises(TypeError):
        check_admissibility("not an equation", symbols={})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# UnitProof contract
# ---------------------------------------------------------------------------


def test_unit_proof_to_canonical_string_has_kind_and_arrow() -> None:
    symbols = {"a": _sym("a", unit="dollar"), "b": _sym("b", unit="dollar")}
    proof = check_admissibility(
        _eq(kind="add", deps=frozenset({"a", "b"})), symbols=symbols
    )
    s = proof.to_canonical_string()
    assert s.startswith("add:")
    assert "->" in s
    assert "money" in s


def test_unit_proof_is_frozen() -> None:
    symbols = {"a": _sym("a", unit="dollar")}
    proof = check_admissibility(
        _eq(kind="add", deps=frozenset({"a"})), symbols=symbols
    )
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        proof.lhs_unit = parse_unit("foot")  # type: ignore[misc]


def test_unit_proof_operand_units_preserved() -> None:
    symbols = {"a": _sym("a", unit="dollar"), "b": _sym("b", unit="dollar")}
    proof = check_admissibility(
        _eq(kind="add", deps=frozenset({"a", "b"})), symbols=symbols
    )
    assert len(proof.operand_units) == 2
    assert all(u == parse_unit("dollar") for u in proof.operand_units)


def test_unit_proof_byte_equal_for_equivalent_inputs() -> None:
    symbols = {"a": _sym("a", unit="dollar"), "b": _sym("b", unit="dollar")}
    p1 = check_admissibility(
        _eq(kind="add", deps=frozenset({"a", "b"})), symbols=symbols
    )
    p2 = check_admissibility(
        _eq(kind="add", deps=frozenset({"a", "b"})), symbols=symbols
    )
    assert p1 == p2
    assert p1.to_canonical_string() == p2.to_canonical_string()


def test_unit_proof_rejects_bad_construction() -> None:
    with pytest.raises(ValueError):
        UnitProof(operation_kind="", lhs_unit=parse_unit("foot"), operand_units=())


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_check_admissibility_deterministic_sorted_dep_iteration() -> None:
    # Same dep set in different insertion order → same proof.
    symbols = {"a": _sym("a", unit="dollar"), "b": _sym("b", unit="dollar")}
    p1 = check_admissibility(
        _eq(kind="add", deps=frozenset(["a", "b"])), symbols=symbols
    )
    p2 = check_admissibility(
        _eq(kind="add", deps=frozenset(["b", "a"])), symbols=symbols
    )
    assert p1 == p2


def test_pack_composite_resolves_to_quotient_in_admissibility() -> None:
    # composite unit resolves through parse_unit; admissibility uses it.
    symbols = {
        "q_actor_hour_t0": _sym("q_actor_hour_t0", unit="hour"),
        "op_000__rate": _sym(
            "op_000__rate", unit="cent_per_hour", role="rate"
        ),
    }
    proof = check_admissibility(
        _eq(
            kind="apply_rate",
            deps=frozenset({"q_actor_hour_t0", "op_000__rate"}),
        ),
        symbols=symbols,
    )
    # cent ∈ units.money → lhs = money
    assert proof.lhs_unit == parse_unit("cent")
