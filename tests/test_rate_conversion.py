"""Tests for the R3.2 exact-rational time-unit conversion primitive."""

from __future__ import annotations

from fractions import Fraction

import pytest

from generate.rate_comprehension.conversion import ConversionError, convert_time, is_convertible


def test_minutes_to_hours_is_exact_rational() -> None:
    assert convert_time(30, "minute", "hour") == Fraction(1, 2)
    assert convert_time(90, "minute", "hour") == Fraction(3, 2)
    assert convert_time(60, "minute", "hour") == Fraction(1)  # exact whole


def test_hours_to_minutes() -> None:
    assert convert_time(2, "hour", "minute") == Fraction(120)


def test_identity_conversion() -> None:
    assert convert_time(5, "hour", "hour") == Fraction(5)


def test_non_time_units_refuse() -> None:
    with pytest.raises(ConversionError):
        convert_time(30, "minute", "mile")
    with pytest.raises(ConversionError):
        convert_time(5, "dollar", "hour")  # currency deferred


def test_is_convertible() -> None:
    assert is_convertible("minute", "hour") and is_convertible("hour", "minute")
    assert not is_convertible("minute", "mile")
    assert not is_convertible("kilometer", "mile")  # length deferred


def test_result_is_never_a_float() -> None:
    result = convert_time(45, "minute", "hour")
    assert isinstance(result, Fraction) and not isinstance(result, float)
    assert result == Fraction(3, 4)
