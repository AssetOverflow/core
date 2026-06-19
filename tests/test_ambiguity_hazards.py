"""Tests for language_packs/ambiguity_hazards.py."""
from __future__ import annotations

import pytest

from language_packs.ambiguity_hazards import (
    lookup_hazards,
    all_hazard_categories,
    all_registered_surfaces,
    is_hazardous,
    AmbiguityHazard,
)


def test_exhaustive_surfaces() -> None:
    expected_surfaces = {
        "half", "quarter", "third", "percent", "percentage points", "times",
        "more than", "less than", "of", "per", "each", "some", "remaining",
        "left", "total", "altogether"
    }
    registered = set(all_registered_surfaces())
    assert expected_surfaces.issubset(registered)

    for s in expected_surfaces:
        assert is_hazardous(s)


def test_exhaustive_categories() -> None:
    expected_categories = {
        "unbound_base_quantity", "half_duration", "quarter_coin",
        "quarter_calendar_period", "quarter_school_term", "third_ordinal",
        "ordinal_context", "currency_context", "temporal_context",
        "percent_change_vs_percent_of", "multiplicative_vs_occurrence_times",
        "comparative_direction_ambiguity", "indefinite_quantity",
        "remainder_context_required", "total_question_target_required",
        "blocked_provenance_gap"
    }
    categories = all_hazard_categories()
    assert expected_categories.issubset(categories)


def test_specific_surface_hazards() -> None:
    # 1. half
    half_hazards = lookup_hazards("half")
    assert len(half_hazards) == 2
    cats = {h.category for h in half_hazards}
    assert cats == {"unbound_base_quantity", "half_duration"}

    # 2. quarter
    quarter_hazards = lookup_hazards("quarter")
    assert len(quarter_hazards) == 4
    cats = {h.category for h in quarter_hazards}
    assert cats == {
        "unbound_base_quantity", "quarter_coin", "quarter_calendar_period",
        "quarter_school_term"
    }

    # 3. some
    some_hazards = lookup_hazards("some")
    assert len(some_hazards) == 1
    assert some_hazards[0].category == "indefinite_quantity"

    # 4. times
    times_hazards = lookup_hazards("times")
    assert len(times_hazards) == 1
    assert times_hazards[0].category == "multiplicative_vs_occurrence_times"


def test_deterministic_ordering() -> None:
    surfaces = all_registered_surfaces()
    assert list(surfaces) == sorted(surfaces)

    for s in surfaces:
        hazards = lookup_hazards(s)
        # Check hazard IDs are sorted
        ids = [h.hazard_id for h in hazards]
        assert ids == sorted(ids)


def test_case_insensitivity() -> None:
    h1 = lookup_hazards("HALF")
    h2 = lookup_hazards("half")
    assert h1 == h2
    assert is_hazardous("HALF")
