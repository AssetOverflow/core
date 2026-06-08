"""Tests for the R3 compound-unit algebra (R3a).

Pins the three single-rate compositions and — load-bearing — that a non-composing operation
REFUSES (``UnitError``) rather than fabricating a unit. The dimensional check is the wrong=0 gate.
"""

from __future__ import annotations

import dataclasses

import pytest

from generate.rate_comprehension.units import (
    BaseUnit,
    RateUnit,
    UnitError,
    rate_from_quantity_over_time,
    rate_times_time,
    time_from_quantity_over_rate,
)

_MPH = RateUnit("mile", "hour")


def test_rate_times_time_composes() -> None:
    assert rate_times_time(_MPH, BaseUnit("hour")) == BaseUnit("mile")


def test_rate_times_wrong_time_refuses() -> None:
    # mile/hour × minute — the time unit is not the rate's denominator.
    with pytest.raises(UnitError):
        rate_times_time(_MPH, BaseUnit("minute"))
    # students/hour × mile.
    with pytest.raises(UnitError):
        rate_times_time(RateUnit("student", "hour"), BaseUnit("mile"))


def test_quantity_over_time_makes_rate() -> None:
    assert rate_from_quantity_over_time(BaseUnit("mile"), BaseUnit("hour")) == _MPH


def test_quantity_over_same_unit_refuses() -> None:
    with pytest.raises(UnitError):
        rate_from_quantity_over_time(BaseUnit("mile"), BaseUnit("mile"))


def test_quantity_over_rate_makes_time() -> None:
    assert time_from_quantity_over_rate(BaseUnit("mile"), _MPH) == BaseUnit("hour")


def test_quantity_over_rate_wrong_numerator_refuses() -> None:
    # dollar ÷ mile/hour — the quantity unit is not the rate's numerator.
    with pytest.raises(UnitError):
        time_from_quantity_over_rate(BaseUnit("dollar"), _MPH)


def test_rate_unit_numerator_equals_denominator_refuses() -> None:
    with pytest.raises(UnitError):
        RateUnit("mile", "mile")


def test_three_operations_compose_consistently() -> None:
    # mile/hour × hour = mile; mile ÷ hour = mile/hour; mile ÷ mile/hour = hour.
    quantity = rate_times_time(_MPH, BaseUnit("hour"))
    assert rate_from_quantity_over_time(quantity, BaseUnit("hour")) == _MPH
    assert time_from_quantity_over_rate(quantity, _MPH) == BaseUnit("hour")


def test_units_are_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _MPH.numerator = "kilometer"  # type: ignore[misc]


def test_empty_unit_name_refuses() -> None:
    with pytest.raises(UnitError):
        BaseUnit("")
