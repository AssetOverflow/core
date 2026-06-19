"""Tests for language_packs/scalar_equivalence.py."""
from __future__ import annotations

from fractions import Fraction
import pytest

from language_packs.scalar_equivalence import (
    canonicalize_scalar,
    is_supported_scalar,
    list_unsupported_surfaces,
    ScalarCandidate,
)


def test_fraction_words_canonicalization() -> None:
    # Single fraction words
    cand = canonicalize_scalar("half")
    assert cand is not None
    assert cand.canonical == Fraction(1, 2)
    assert cand.source == "fraction_word"
    assert cand.entry_id is not None
    assert len(cand.hazards) > 0
    assert all(h.startswith("haz-") for h in cand.hazards)

    cand = canonicalize_scalar("third")
    assert cand is not None
    assert cand.canonical == Fraction(1, 3)
    assert cand.source == "fraction_word"

    cand = canonicalize_scalar("quarter")
    assert cand is not None
    assert cand.canonical == Fraction(1, 4)
    assert cand.source == "fraction_word"

    # Compound fraction words
    cand = canonicalize_scalar("one half")
    assert cand is not None
    assert cand.canonical == Fraction(1, 2)

    cand = canonicalize_scalar("one-half")
    assert cand is not None
    assert cand.canonical == Fraction(1, 2)

    cand = canonicalize_scalar("three quarters")
    assert cand is not None
    assert cand.canonical == Fraction(3, 4)


def test_decimals_canonicalization() -> None:
    cand = canonicalize_scalar("0.5")
    assert cand is not None
    assert cand.canonical == Fraction(1, 2)
    assert cand.source == "decimal"

    cand = canonicalize_scalar("0.25")
    assert cand is not None
    assert cand.canonical == Fraction(1, 4)

    cand = canonicalize_scalar("0.75")
    assert cand is not None
    assert cand.canonical == Fraction(3, 4)


def test_percentages_canonicalization() -> None:
    cand = canonicalize_scalar("50%")
    assert cand is not None
    assert cand.canonical == Fraction(1, 2)
    assert cand.source == "percentage"

    cand = canonicalize_scalar("25%")
    assert cand is not None
    assert cand.canonical == Fraction(1, 4)

    cand = canonicalize_scalar("75%")
    assert cand is not None
    assert cand.canonical == Fraction(3, 4)

    cand = canonicalize_scalar("100%")
    assert cand is not None
    assert cand.canonical == Fraction(1, 1)


def test_slash_fractions_canonicalization() -> None:
    cand = canonicalize_scalar("1/2")
    assert cand is not None
    assert cand.canonical == Fraction(1, 2)
    assert cand.source == "slash_fraction"

    cand = canonicalize_scalar("3/4")
    assert cand is not None
    assert cand.canonical == Fraction(3, 4)


def test_unicode_fractions() -> None:
    for sym, val in [("½", Fraction(1, 2)), ("¼", Fraction(1, 4)), ("¾", Fraction(3, 4)), ("⅓", Fraction(1, 3)), ("⅔", Fraction(2, 3))]:
        cand = canonicalize_scalar(sym)
        assert cand is not None, f"Failed on {sym}"
        assert cand.canonical == val, f"Expected {val} for {sym}, got {cand.canonical}"
        assert cand.source == "fraction_symbol"


def test_unsupported_surfaces() -> None:
    unsupported = list_unsupported_surfaces()
    assert ".5" in unsupported
    assert "1 / 2" in unsupported

    for surface in unsupported:
        assert canonicalize_scalar(surface) is None
        assert not is_supported_scalar(surface)


def test_is_supported_scalar() -> None:
    assert is_supported_scalar("half")
    assert is_supported_scalar("0.5")
    assert is_supported_scalar("50%")
    assert is_supported_scalar("1/2")
    assert not is_supported_scalar(".5")
    assert not is_supported_scalar("1 / 2")
    assert not is_supported_scalar("random_string")
