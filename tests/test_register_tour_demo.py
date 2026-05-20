"""Register tour demo — load-bearing seam claim (ADR-0072 / R5).

Pins the three seam claims:

* grounding_source identical across {neutral, terse, convivial} per prompt
* trace_hash identical across {neutral, terse, convivial} per prompt
* surface differs at least once (convivial vs neutral)

Any one of those failing is the R5 architectural-regression signal.
"""

from __future__ import annotations

from evals.register_tour.run_tour import _PROMPTS, _REGISTERS, run_tour


def test_tour_returns_structured_report():
    report = run_tour(emit_json=True)
    assert set(report) >= {
        "registers", "prompts", "grid", "claims", "all_claims_supported",
    }
    assert list(report["registers"]) == list(_REGISTERS)
    assert list(report["prompts"]) == list(_PROMPTS)


def test_tour_grounding_sources_identical_across_registers():
    report = run_tour(emit_json=True)
    assert report["claims"]["all_grounding_sources_identical"] is True


def test_tour_trace_hashes_identical_across_registers():
    """ADR-0069 invariant C, restated as a falsifiable demo claim."""
    report = run_tour(emit_json=True)
    assert report["claims"]["all_trace_hashes_identical"] is True


def test_tour_surfaces_vary_at_least_once():
    """ADR-0071 seeded variation: convivial vs neutral must differ
    somewhere across the four-prompt sequence."""
    report = run_tour(emit_json=True)
    assert report["claims"]["surfaces_vary_at_least_once"] is True


def test_tour_all_claims_supported():
    """Canonical R5 gate — every claim must hold or exit non-zero."""
    report = run_tour(emit_json=True)
    assert report["all_claims_supported"] is True


def test_tour_grid_carries_register_id_per_cell():
    """Each grid cell records the register_id that produced it."""
    report = run_tour(emit_json=True)
    for register_id in _REGISTERS:
        cells = report["grid"][register_id]
        assert len(cells) == len(_PROMPTS)
        for cell in cells:
            assert cell["register_id"] == register_id


def test_tour_grid_variant_id_empty_when_no_decoration():
    """terse_v1 + default_neutral_v1 emit empty variant_ids; convivial_v1
    emits non-empty variant_ids on non-empty surfaces."""
    report = run_tour(emit_json=True)
    for cell in report["grid"]["default_neutral_v1"]:
        assert cell["register_variant_id"] == ""
    for cell in report["grid"]["terse_v1"]:
        assert cell["register_variant_id"] == ""
    convivial_non_empty = [
        c for c in report["grid"]["convivial_v1"]
        if c["surface"]
    ]
    assert any(c["register_variant_id"] != "" for c in convivial_non_empty)
