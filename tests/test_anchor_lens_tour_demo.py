"""Anchor-lens tour demo — load-bearing seam claims (ADR-0073d / L1.4).

Pins the four seam claims:

* lens_ids_recorded_per_turn               — telemetry visibility holds.
* trace_hashes_distinct_across_lenses      — substantive lift fires.
* surface_propositions_distinct_across_lenses — surface lift fires.
* no_substrate_glyph_leak                  — ASCII contract holds.

Any one failing is the L1.4 architectural-regression signal.
"""

from __future__ import annotations

from evals.anchor_lens_tour.run_tour import _LENSES, _PROMPTS, run_tour


def test_tour_returns_structured_report():
    report = run_tour(emit_json=True)
    assert set(report) >= {
        "lenses", "prompts", "grid", "claims", "all_claims_supported",
    }
    assert list(report["lenses"]) == list(_LENSES)
    assert list(report["prompts"]) == list(_PROMPTS)


def test_tour_lens_ids_recorded_per_turn():
    report = run_tour(emit_json=True)
    assert report["claims"]["lens_ids_recorded_per_turn"] is True


def test_tour_trace_hashes_distinct_across_lenses():
    """L1.3 lift claim, restated as a falsifiable demo invariant — and
    the *opposite* of register-tour's trace_hashes_identical claim."""
    report = run_tour(emit_json=True)
    assert report["claims"]["trace_hashes_distinct_across_lenses"] is True


def test_tour_surface_propositions_distinct_across_lenses():
    report = run_tour(emit_json=True)
    assert report["claims"]["surface_propositions_distinct_across_lenses"] is True


def test_tour_no_substrate_glyph_leak():
    """ADR-0073c hard gate, re-asserted in tour scope."""
    report = run_tour(emit_json=True)
    assert report["claims"]["no_substrate_glyph_leak"] is True
    assert report["claims"]["glyph_violations"] == []


def test_tour_all_claims_supported():
    """Canonical L1.4 gate — every claim must hold or exit non-zero."""
    report = run_tour(emit_json=True)
    assert report["all_claims_supported"] is True


def test_tour_grid_carries_anchor_lens_id_per_cell():
    """Each grid cell records the lens that produced it."""
    report = run_tour(emit_json=True)
    for lens_id in _LENSES:
        cells = report["grid"][lens_id]
        assert len(cells) == len(_PROMPTS)
        for cell in cells:
            assert cell["anchor_lens_id"] == lens_id


def test_tour_unanchored_cells_have_empty_mode_label():
    """The unanchored baseline never engages, so its mode_label is
    always empty regardless of prompt."""
    report = run_tour(emit_json=True)
    for cell in report["grid"]["default_unanchored_v1"]:
        assert cell["anchor_lens_mode_label"] == ""


def test_tour_engaged_cells_carry_mode_label():
    """grc_logos_v1 engages on knowledge; he_logos_v1 engages on truth."""
    report = run_tour(emit_json=True)
    grc_knowledge = next(
        c for c in report["grid"]["grc_logos_v1"]
        if c["prompt"] == "What is knowledge?"
    )
    assert grc_knowledge["anchor_lens_mode_label"] == "systematic"
    he_truth = next(
        c for c in report["grid"]["he_logos_v1"]
        if c["prompt"] == "What is truth?"
    )
    assert he_truth["anchor_lens_mode_label"] == "covenant-verity"
