from __future__ import annotations

import pytest
from language_packs.loader import (
    lookup_unit,
    lookup_container,
    lookup_dimension,
    get_conversion_graph,
    canonical_unit_for,
    UnitEntry,
    ContainerEntry,
    DimensionEntry,
)

def test_lookup_unit_happy_path() -> None:
    # Singular
    u_foot = lookup_unit("foot")
    assert isinstance(u_foot, UnitEntry)
    assert u_foot.singular == "foot"
    assert u_foot.plural == "feet"
    assert u_foot.symbol == "ft"
    assert u_foot.dimension == "length"
    assert u_foot.is_canonical_for_dimension is True

    # Plural
    u_feet = lookup_unit("feet")
    assert isinstance(u_feet, UnitEntry)
    assert u_feet.singular == "foot"
    assert u_feet.plural == "feet"

    # Symbol
    u_ft = lookup_unit("ft")
    assert isinstance(u_ft, UnitEntry)
    assert u_ft.singular == "foot"
    assert u_ft.plural == "feet"


def test_lookup_unit_missing_returns_none() -> None:
    assert lookup_unit("not_a_unit") is None
    assert lookup_unit("") is None


def test_lookup_container() -> None:
    # Singular
    c_box = lookup_container("box")
    assert isinstance(c_box, ContainerEntry)
    assert c_box.singular == "box"
    assert c_box.plural == "boxes"
    assert c_box.default_size is None

    # Plural
    c_boxes = lookup_container("boxes")
    assert isinstance(c_boxes, ContainerEntry)
    assert c_boxes.singular == "box"

    # Container with default size
    c_dozen = lookup_container("dozen")
    assert c_dozen.default_size == 12

    c_pair = lookup_container("pair")
    assert c_pair.default_size == 2

    c_gross = lookup_container("gross")
    assert c_gross.default_size == 144

    # Missing
    assert lookup_container("not_a_container") is None


def test_lookup_dimension() -> None:
    d_length = lookup_dimension("length")
    assert isinstance(d_length, DimensionEntry)
    assert d_length.name == "length"
    assert d_length.canonical_unit == "foot"
    assert d_length.is_derived is False

    d_area = lookup_dimension("area")
    assert isinstance(d_area, DimensionEntry)
    assert d_area.name == "area"
    assert d_area.canonical_unit == "square_foot"
    assert d_area.is_derived is True
    assert d_area.formula == "length * length"

    # Missing
    assert lookup_dimension("not_a_dimension") is None


def test_canonical_unit_for() -> None:
    assert canonical_unit_for("length") == "foot"
    assert canonical_unit_for("time") == "minute"
    with pytest.raises(ValueError, match="Unknown dimension"):
        canonical_unit_for("not_a_dimension")


def test_multi_word_composition_area_volume() -> None:
    # Area
    u_sq_in = lookup_unit("square inch")
    assert isinstance(u_sq_in, UnitEntry)
    assert u_sq_in.dimension == "area"
    assert u_sq_in.singular == "square inch"
    assert u_sq_in.plural == "square inches"
    assert u_sq_in.is_canonical_for_dimension is False

    u_sq_ft = lookup_unit("square feet")
    assert isinstance(u_sq_ft, UnitEntry)
    assert u_sq_ft.dimension == "area"
    assert u_sq_ft.is_canonical_for_dimension is True

    # Volume (cubic length-unit)
    u_cu_m = lookup_unit("cubic meter")
    assert isinstance(u_cu_m, UnitEntry)
    assert u_cu_m.dimension == "volume"
    assert u_cu_m.singular == "cubic meter"
    assert u_cu_m.plural == "cubic meters"
    assert u_cu_m.is_canonical_for_dimension is False


def test_multi_word_composition_speed_density() -> None:
    # Speed
    u_mps = lookup_unit("meters per second")
    assert isinstance(u_mps, UnitEntry)
    assert u_mps.dimension == "speed"
    assert u_mps.singular == "meter per second"
    assert u_mps.plural == "meters per second"
    assert u_mps.is_canonical_for_dimension is False

    u_mph = lookup_unit("miles per hour")
    assert isinstance(u_mph, UnitEntry)
    assert u_mph.dimension == "speed"
    assert u_mph.is_canonical_for_dimension is True

    # Density
    u_dens = lookup_unit("pounds per cubic foot")
    assert isinstance(u_dens, UnitEntry)
    assert u_dens.dimension == "density"
    assert u_dens.singular == "pound per cubic foot"
    assert u_dens.is_canonical_for_dimension is True


def test_multi_word_composition_wage_unit_price() -> None:
    # Wage (money per time)
    u_wage = lookup_unit("dollars per hour")
    assert isinstance(u_wage, UnitEntry)
    assert u_wage.dimension == "wage"
    assert u_wage.singular == "dollar per hour"
    assert u_wage.plural == "dollars per hour"

    # Unit price (money per count/token)
    u_price = lookup_unit("dollars per item")
    assert isinstance(u_price, UnitEntry)
    assert u_price.dimension == "unit_price"
    assert u_price.singular == "dollar per item"

    u_price_apple = lookup_unit("cents per apple")
    assert isinstance(u_price_apple, UnitEntry)
    assert u_price_apple.dimension == "unit_price"
    assert u_price_apple.singular == "cent per apple"
