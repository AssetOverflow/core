"""ADR-0134 — Unit algebra primitives.

Pure algebra over the closed dimensional vocabulary in ``en_units_v1``.
No I/O at call time; no coercion; refusal-first on unknown ids.
"""

from __future__ import annotations

import pytest

from generate.binding_graph.units import (
    BASE_DIMENSIONS,
    DIMENSIONLESS,
    UnitAlgebraError,
    UnitVector,
    parse_unit,
    unit_inverse,
    unit_product,
    unit_quotient,
    units_equal,
)

# ---------------------------------------------------------------------------
# UnitVector construction
# ---------------------------------------------------------------------------


def test_base_dimensions_are_load_bearing_closed_tuple() -> None:
    assert isinstance(BASE_DIMENSIONS, tuple)
    assert len(BASE_DIMENSIONS) == 6
    assert set(BASE_DIMENSIONS) == {
        "length",
        "time",
        "mass",
        "money",
        "count",
        "temperature",
    }


def test_dimensionless_is_all_zero() -> None:
    assert DIMENSIONLESS.exponents == (0, 0, 0, 0, 0, 0)


def test_unit_vector_requires_tuple() -> None:
    with pytest.raises(UnitAlgebraError):
        UnitVector(exponents=[1, 0, 0, 0, 0, 0])  # type: ignore[arg-type]


def test_unit_vector_requires_correct_arity() -> None:
    with pytest.raises(UnitAlgebraError):
        UnitVector(exponents=(1, 0, 0))


def test_unit_vector_rejects_non_int_exponents() -> None:
    with pytest.raises(UnitAlgebraError):
        UnitVector(exponents=(1.0, 0, 0, 0, 0, 0))  # type: ignore[arg-type]


def test_unit_vector_rejects_bool_exponents() -> None:
    with pytest.raises(UnitAlgebraError):
        UnitVector(exponents=(True, 0, 0, 0, 0, 0))  # type: ignore[arg-type]


def test_unit_vector_is_frozen() -> None:
    v = UnitVector(exponents=(1, 0, 0, 0, 0, 0))
    with pytest.raises(Exception):
        v.exponents = (0, 0, 0, 0, 0, 0)  # type: ignore[misc]


def test_unit_vector_canonical_string_dimensionless() -> None:
    assert DIMENSIONLESS.to_canonical_string() == "dimensionless"


def test_unit_vector_canonical_string_simple_numerator() -> None:
    assert parse_unit("foot").to_canonical_string() == "length"


def test_unit_vector_canonical_string_squared() -> None:
    assert parse_unit("square_foot").to_canonical_string() == "length^2"


def test_unit_vector_canonical_string_quotient() -> None:
    assert parse_unit("mile_per_hour").to_canonical_string() == "length/time"


def test_unit_vector_canonical_string_inverse_only() -> None:
    inv = unit_inverse(parse_unit("hour"))
    assert inv.to_canonical_string() == "1/time"


# ---------------------------------------------------------------------------
# parse_unit
# ---------------------------------------------------------------------------


def test_parse_unit_exact_pack_lemma_money() -> None:
    assert parse_unit("dollar").exponents == (0, 0, 0, 1, 0, 0)


def test_parse_unit_exact_pack_lemma_length() -> None:
    assert parse_unit("foot").exponents == (1, 0, 0, 0, 0, 0)


def test_parse_unit_exact_pack_lemma_mass() -> None:
    assert parse_unit("pound").exponents == (0, 0, 1, 0, 0, 0)


def test_parse_unit_exact_pack_lemma_count() -> None:
    assert parse_unit("item").exponents == (0, 0, 0, 0, 1, 0)


def test_parse_unit_exact_pack_lemma_temperature() -> None:
    assert parse_unit("Celsius").exponents == (0, 0, 0, 0, 0, 1)


def test_parse_unit_derived_speed() -> None:
    assert parse_unit("mile_per_hour").exponents == (1, -1, 0, 0, 0, 0)


def test_parse_unit_derived_wage() -> None:
    assert parse_unit("dollar_per_hour").exponents == (0, -1, 0, 1, 0, 0)


def test_parse_unit_depluralize_s() -> None:
    assert units_equal(parse_unit("dollars"), parse_unit("dollar"))


def test_parse_unit_depluralize_es() -> None:
    # 'inches' → 'inch'
    assert units_equal(parse_unit("inches"), parse_unit("inch"))


def test_parse_unit_depluralize_ies() -> None:
    # 'centuries' → 'century'
    assert units_equal(parse_unit("centuries"), parse_unit("century"))


def test_parse_unit_dimensionless_symbol() -> None:
    # Pack 'units.symbol' lemmas (e.g., 'percent') are dimensionless.
    assert units_equal(parse_unit("percent"), DIMENSIONLESS)


def test_parse_unit_container_is_count_dim() -> None:
    assert parse_unit("dozen").exponents == (0, 0, 0, 0, 1, 0)


def test_parse_unit_composite_decomposes() -> None:
    # foot_per_second → length/time
    assert parse_unit("foot_per_second").exponents == (1, -1, 0, 0, 0, 0)


def test_parse_unit_composite_with_unknown_inner_refuses() -> None:
    with pytest.raises(UnitAlgebraError) as ei:
        parse_unit("dollar_per_apple")
    assert "unknown_unit" in str(ei.value)


def test_parse_unit_unknown_refuses() -> None:
    with pytest.raises(UnitAlgebraError) as ei:
        parse_unit("apples")
    assert "unknown_unit" in str(ei.value)


def test_parse_unit_unknown_widgets_refuses() -> None:
    with pytest.raises(UnitAlgebraError):
        parse_unit("widgets")


def test_parse_unit_empty_string_refuses() -> None:
    with pytest.raises(UnitAlgebraError):
        parse_unit("")


def test_parse_unit_non_string_refuses() -> None:
    with pytest.raises(UnitAlgebraError):
        parse_unit(None)  # type: ignore[arg-type]


def test_parse_unit_rate_connector_not_a_unit() -> None:
    # 'per' is a connector in units.rate; refuse rather than treat as a unit.
    with pytest.raises(UnitAlgebraError):
        parse_unit("per")


def test_parse_unit_dimension_header_not_a_unit() -> None:
    # 'length' is a dimension header; the lemma is in units.dimension and
    # must be rejected — only concrete units resolve.
    with pytest.raises(UnitAlgebraError):
        parse_unit("length")


# ---------------------------------------------------------------------------
# Algebra primitives
# ---------------------------------------------------------------------------


def test_unit_product_commutes() -> None:
    a, b = parse_unit("foot"), parse_unit("hour")
    assert unit_product(a, b).exponents == unit_product(b, a).exponents


def test_unit_product_byte_equal_swap() -> None:
    a, b = parse_unit("foot"), parse_unit("hour")
    assert unit_product(a, b) == unit_product(b, a)


def test_unit_product_squares_length() -> None:
    foot = parse_unit("foot")
    assert unit_product(foot, foot).exponents == (2, 0, 0, 0, 0, 0)


def test_unit_quotient_speed() -> None:
    # foot / second = speed (length/time)
    q = unit_quotient(parse_unit("foot"), parse_unit("second"))
    assert q.exponents == (1, -1, 0, 0, 0, 0)


def test_unit_quotient_not_commutative() -> None:
    a, b = parse_unit("foot"), parse_unit("hour")
    assert unit_quotient(a, b).exponents != unit_quotient(b, a).exponents


def test_unit_inverse_of_inverse_is_identity() -> None:
    v = parse_unit("dollar_per_hour")
    assert unit_inverse(unit_inverse(v)) == v


def test_unit_inverse_of_dimensionless_is_dimensionless() -> None:
    assert unit_inverse(DIMENSIONLESS) == DIMENSIONLESS


def test_unit_quotient_self_is_dimensionless() -> None:
    foot = parse_unit("foot")
    assert unit_quotient(foot, foot) == DIMENSIONLESS


def test_unit_product_with_dimensionless_is_identity() -> None:
    foot = parse_unit("foot")
    assert unit_product(foot, DIMENSIONLESS) == foot


def test_units_equal_reflexive() -> None:
    foot = parse_unit("foot")
    assert units_equal(foot, foot)


def test_units_equal_strict_on_dimensions() -> None:
    assert not units_equal(parse_unit("foot"), parse_unit("hour"))


def test_units_equal_strict_on_exponent_magnitude() -> None:
    foot = parse_unit("foot")
    sq = unit_product(foot, foot)
    assert not units_equal(foot, sq)


def test_unit_algebra_no_io_at_call_time(tmp_path, monkeypatch) -> None:
    # After first call the pack lexicon is memoized; subsequent calls must
    # not touch the filesystem. Smoke this by pointing the resolver path at
    # an invalid location post-warmup; calls must still succeed.
    import generate.binding_graph.units as U

    _ = parse_unit("foot")  # warm cache
    monkeypatch.setattr(U, "_UNITS_PACK_LEXICON", tmp_path / "missing.jsonl")
    # Cached table is still in use.
    assert parse_unit("foot").exponents == (1, 0, 0, 0, 0, 0)


def test_parse_unit_idempotent_across_repeat_calls() -> None:
    a = parse_unit("dollar_per_hour")
    b = parse_unit("dollar_per_hour")
    assert a == b
    assert a.exponents == b.exponents


def test_unit_vector_is_hashable() -> None:
    # Frozen dataclasses are hashable by default; the binding graph relies
    # on this when comparing UnitProof tuples.
    assert hash(parse_unit("foot")) == hash(parse_unit("foot"))
