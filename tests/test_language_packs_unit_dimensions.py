"""Tests for language_packs/unit_dimensions.py."""
from __future__ import annotations

from fractions import Fraction
import pytest

from language_packs.unit_dimensions import (
    classify_dimension,
    are_dimensions_compatible,
    exact_conversion,
    classify_rate_dimension,
    supported_dimension_families,
    DimensionFact,
    ConversionFact,
)


def test_classify_dimension() -> None:
    # 1. Base dimensions
    fact = classify_dimension("inch")
    assert fact is not None
    assert fact.surface == "inch"
    assert fact.dimension == "length"
    assert fact.singular == "inch"
    assert fact.plural == "inches"
    assert not fact.is_derived
    assert fact.provenance_kind == "kernel_unit"

    fact = classify_dimension("dollars")
    assert fact is not None
    assert fact.dimension == "money"
    assert fact.singular == "dollar"
    assert fact.plural == "dollars"

    fact = classify_dimension("hours")
    assert fact is not None
    assert fact.dimension == "time"
    assert fact.singular == "hour"
    assert fact.plural == "hours"

    fact = classify_dimension("items")
    assert fact is not None
    assert fact.dimension == "count"
    assert fact.singular == "item"
    assert fact.plural == "items"

    # 2. Derived/Rate dimensions
    fact = classify_dimension("dollar per hour")
    assert fact is not None
    assert fact.dimension == "wage"
    assert fact.is_derived

    # 3. Unsupported / Not found
    assert classify_dimension("unknown_unit_name") is None
    assert classify_dimension("") is None


def test_are_dimensions_compatible() -> None:
    # Same base dimensions
    assert are_dimensions_compatible("length", "length")
    assert are_dimensions_compatible("time", "time")

    # Mismatched base dimensions
    assert not are_dimensions_compatible("length", "time")
    assert not are_dimensions_compatible("money", "count")

    # Rate dimensions compatibility
    assert are_dimensions_compatible("wage", "wage")
    assert are_dimensions_compatible("speed", "speed")

    # Rate and base
    assert not are_dimensions_compatible("wage", "money")
    assert not are_dimensions_compatible("speed", "length")


def test_classify_rate_dimension() -> None:
    assert classify_rate_dimension("money", "time") == "wage"
    assert classify_rate_dimension("length", "time") == "speed"
    assert classify_rate_dimension("money", "count") == "unit_price"
    assert classify_rate_dimension("count", "time") == "frequency"
    assert classify_rate_dimension("mass", "volume") == "density"
    assert classify_rate_dimension("count", "container") == "items_per_container"
    assert classify_rate_dimension("length", "money") is None


def test_exact_conversion() -> None:
    # Feet to inches
    conv = exact_conversion("foot", "inch")
    assert conv is not None
    assert conv.from_unit == "foot"
    assert conv.to_unit == "inch"
    assert conv.ratio == Fraction(12, 1)
    assert conv.dimension == "length"
    assert conv.provenance_kind == "kernel_unit"

    # Inches to feet
    conv = exact_conversion("inch", "foot")
    assert conv is not None
    assert conv.ratio == Fraction(1, 12)

    # Dollars to cents
    conv = exact_conversion("dollar", "cent")
    assert conv is not None
    assert conv.ratio == Fraction(100, 1)

    # Hours to minutes
    conv = exact_conversion("hour", "minute")
    assert conv is not None
    assert conv.ratio == Fraction(60, 1)

    # Incompatible conversion
    assert exact_conversion("foot", "dollar") is None
    assert exact_conversion("unknown", "inch") is None


def test_supported_dimension_families() -> None:
    families = supported_dimension_families()
    assert "count" in families
    assert "length" in families
    assert "money" in families
    assert "time" in families
    assert list(families) == sorted(families)
