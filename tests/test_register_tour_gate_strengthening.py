"""ADR-0077 (R6) — register-tour gate strengthening tests.

Pins the gate's new falsifiability properties:

* The real ratified register-pack triple passes every claim.
* Synthetic terse_v1 with all R6 knobs = false would FAIL the new
  ``terse_substantively_differs`` claim (proving the old
  ``surfaces_vary_at_least_once`` hole is closed).
* Synthetic convivial_v1 with ``append_semantic_domain_clause = false``
  would FAIL the new ``convivial_substantively_differs`` claim.

Together these prove the gate is load-bearing — it can fail, and it
fails on exactly the regression shape R6 was designed to prevent.
"""

from __future__ import annotations

import pytest

from evals.register_tour.run_tour import (
    _DEFINITION_PROMPTS,
    _check_claims,
    _substantively_differs,
    run_tour,
)


# ---------- Real packs pass every claim ----------


@pytest.fixture(scope="module")
def real_tour_report():
    return run_tour(emit_json=True)


def test_real_tour_passes_all_claims(real_tour_report):
    assert real_tour_report["all_claims_supported"] is True


def test_real_tour_all_grounding_sources_identical(real_tour_report):
    assert real_tour_report["claims"]["all_grounding_sources_identical"]


def test_real_tour_all_trace_hashes_identical(real_tour_report):
    assert real_tour_report["claims"]["all_trace_hashes_identical"]


def test_real_tour_register_canonical_surfaces_identical(real_tour_report):
    """ADR-0077 invariant_register_canonical_surface_constant_across_registers."""
    assert real_tour_report["claims"]["register_canonical_surfaces_identical"]


def test_real_tour_terse_substantively_differs(real_tour_report):
    """ADR-0077 invariant_terse_substantively_distinct_from_neutral."""
    assert real_tour_report["claims"][
        "terse_substantively_differs_from_neutral_on_pack_grounded_definition"
    ]


def test_real_tour_convivial_substantively_differs(real_tour_report):
    """ADR-0077 invariant_convivial_substantively_distinct_from_neutral."""
    assert real_tour_report["claims"][
        "convivial_substantively_differs_from_neutral_on_pack_grounded_definition"
    ]


# ---------- _substantively_differs helper ----------


def test_substantive_differ_helper_byte_identical_returns_false():
    assert _substantively_differs("hello", "hello") is False


def test_substantive_differ_helper_whitespace_only_returns_false():
    """The whole point of the helper: pure whitespace shifts must
    NOT count as substantive difference."""
    assert _substantively_differs("hello world", "hello  world") is False


def test_substantive_differ_helper_punctuation_only_returns_false():
    """Trailing-period differences (e.g. ``"."`` vs ``""``) must NOT
    count as substantive — those are exactly the kinds of cosmetic
    artifacts R6 is supposed to ignore in the gate."""
    assert _substantively_differs("hello.", "hello") is False
    assert _substantively_differs("hello,", "hello;") is False


def test_substantive_differ_helper_real_word_change_returns_true():
    assert _substantively_differs("hello world", "hello earth") is True


def test_substantive_differ_helper_removed_word_returns_true():
    assert _substantively_differs("the cat sits", "cat sits") is True


# ---------- Falsifiability: synthetic regressed grid would fail ----------


def _synthetic_grid_terse_regressed():
    """Build a synthetic tour grid where terse_v1 is byte-identical to
    neutral on every prompt — the regression shape the strengthened
    gate must catch.

    Reuses the real neutral cells (the regression we're simulating is
    "terse went no-op", not "neutral changed").  Convivial keeps its
    real surfaces so only the terse claim fails.
    """
    from evals.register_tour.run_tour import _REGISTERS, _run_one_register
    grid = {r: _run_one_register(r) for r in _REGISTERS}
    # Synthetically force terse to mirror neutral byte-for-byte.
    for prompt_idx in range(len(grid["default_neutral_v1"])):
        neutral_cell = grid["default_neutral_v1"][prompt_idx]
        terse_cell = dict(grid["terse_v1"][prompt_idx])
        terse_cell["surface"] = neutral_cell["surface"]
        grid["terse_v1"][prompt_idx] = terse_cell
    return grid


def _synthetic_grid_convivial_regressed():
    """Same idea for convivial: regress convivial to neutral surfaces."""
    from evals.register_tour.run_tour import _REGISTERS, _run_one_register
    grid = {r: _run_one_register(r) for r in _REGISTERS}
    for prompt_idx in range(len(grid["default_neutral_v1"])):
        neutral_cell = grid["default_neutral_v1"][prompt_idx]
        conv_cell = dict(grid["convivial_v1"][prompt_idx])
        conv_cell["surface"] = neutral_cell["surface"]
        grid["convivial_v1"][prompt_idx] = conv_cell
    return grid


def test_regressed_terse_fails_strengthened_gate():
    """When terse_v1 produces byte-identical surfaces to neutral, the
    new gate must fail (the old ``surfaces_vary_at_least_once`` would
    have passed because convivial still varies)."""
    grid = _synthetic_grid_terse_regressed()
    claims = _check_claims(grid)
    assert claims[
        "terse_substantively_differs_from_neutral_on_pack_grounded_definition"
    ] is False
    # Other claims still hold.
    assert claims["all_grounding_sources_identical"]
    assert claims["all_trace_hashes_identical"]
    assert claims["register_canonical_surfaces_identical"]


def test_regressed_convivial_fails_strengthened_gate():
    grid = _synthetic_grid_convivial_regressed()
    claims = _check_claims(grid)
    assert claims[
        "convivial_substantively_differs_from_neutral_on_pack_grounded_definition"
    ] is False


def test_definition_prompts_are_in_tour():
    """Sanity: at least three DEFINITION prompts are exercised by the
    tour.  Without this, the strengthened gate could trivially pass
    on an empty set."""
    from evals.register_tour.run_tour import _PROMPTS
    overlap = set(_DEFINITION_PROMPTS) & set(_PROMPTS)
    assert len(overlap) >= 3
