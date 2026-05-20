"""Orthogonality tour demo — composition gate (ADR-0074).

Pins the five composed claims that the single-axis tours only assert
in isolation:

  A) inner_register_invariant_within_lens
  B) outer_lens_distinctness_within_register
  C) surface_carries_register_marker_under_convivial
  D) surface_carries_lens_annotation_when_engaged
  E) no_substrate_glyph_leak_across_grid

Any one failing is the composition-regression signal.
"""

from __future__ import annotations

from evals.orthogonality_tour.run_tour import (
    _LENSES,
    _PROMPTS,
    _REGISTERS,
    run_tour,
)


def test_tour_returns_structured_report():
    report = run_tour(emit_json=True)
    assert set(report) >= {
        "registers", "lenses", "prompts", "cells", "claims",
        "all_claims_supported",
    }
    assert list(report["registers"]) == list(_REGISTERS)
    assert list(report["lenses"]) == list(_LENSES)
    assert list(report["prompts"]) == list(_PROMPTS)


def test_grid_has_18_cells():
    """3 registers × 3 lenses × 2 prompts."""
    report = run_tour(emit_json=True)
    assert len(report["cells"]) == 18


def test_claim_A_register_invariant_within_each_lens():
    """Inner register-tour: for every (lens, prompt) the three
    register runs share an identical trace_hash."""
    report = run_tour(emit_json=True)
    assert report["claims"]["inner_register_invariant_within_lens"] is True
    assert report["claims"]["register_invariant_failures"] == []


def test_claim_B_lens_distinctness_within_each_register():
    """Inner anchor-lens-tour: engaged lenses diverge from the
    unanchored baseline at every (register, prompt) cell."""
    report = run_tour(emit_json=True)
    assert report["claims"]["outer_lens_distinctness_within_register"] is True
    assert report["claims"]["lens_distinctness_failures"] == []


def test_claim_C_convivial_carries_register_marker():
    report = run_tour(emit_json=True)
    assert report["claims"]["surface_carries_register_marker_under_convivial"] is True
    assert report["claims"]["convivial_marker_failures"] == []


def test_claim_D_engaged_lens_carries_annotation():
    report = run_tour(emit_json=True)
    assert report["claims"]["surface_carries_lens_annotation_when_engaged"] is True
    assert report["claims"]["lens_annotation_failures"] == []


def test_claim_E_no_substrate_glyph_leak_across_grid():
    report = run_tour(emit_json=True)
    assert report["claims"]["no_substrate_glyph_leak_across_grid"] is True
    assert report["claims"]["glyph_violations"] == []


def test_all_claims_supported():
    """Canonical composition gate — every claim must hold or exit non-zero."""
    report = run_tour(emit_json=True)
    assert report["all_claims_supported"] is True


def test_engaged_cells_appear_for_both_non_trivial_lenses():
    """Sanity: the grid actually exercises engagement.  grc_logos_v1
    engages on knowledge; he_logos_v1 engages on truth.  Each
    non-trivial lens must produce at least one engaged cell
    (otherwise the lift claim is vacuously satisfied)."""
    report = run_tour(emit_json=True)
    grc_engaged = [
        c for c in report["cells"]
        if c["lens_id"] == "grc_logos_v1"
        and c["anchor_lens_mode_label"] == "systematic"
    ]
    he_engaged = [
        c for c in report["cells"]
        if c["lens_id"] == "he_logos_v1"
        and c["anchor_lens_mode_label"] == "covenant-verity"
    ]
    # grc engages on knowledge in every register (3 cells); same for he on truth.
    assert len(grc_engaged) == len(_REGISTERS), (
        f"expected grc_logos_v1 engagement in {len(_REGISTERS)} cells "
        f"(once per register on 'What is knowledge?'), got {len(grc_engaged)}"
    )
    assert len(he_engaged) == len(_REGISTERS), (
        f"expected he_logos_v1 engagement in {len(_REGISTERS)} cells "
        f"(once per register on 'What is truth?'), got {len(he_engaged)}"
    )
