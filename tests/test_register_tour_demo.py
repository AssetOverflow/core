"""Register tour demo — load-bearing seam claims (ADR-0072 R5 +
ADR-0077 R6).

Pins the strengthened gate:

* grounding_source identical across {neutral, terse, convivial} per prompt
* trace_hash identical across {neutral, terse, convivial} per prompt
* register_canonical_surface identical across registers per prompt
  (R6 layering separation)
* terse substantively differs from neutral on at least one
  pack-grounded DEFINITION prompt (R6 falsifiability)
* convivial substantively differs from neutral on at least one
  pack-grounded DEFINITION prompt (R6 falsifiability)

Any one of those failing is the R5/R6 architectural-regression signal.
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


def test_tour_terse_substantively_differs_from_neutral():
    """ADR-0077 (R6) — replaces the old ``surfaces_vary_at_least_once``
    claim, which convivial's decorative wrapper alone could satisfy.
    The new gate fires only on DEFINITION + pack-grounded prompts and
    requires terse_v1 to differ from default_neutral_v1 on more than
    whitespace/punctuation."""
    report = run_tour(emit_json=True)
    assert report["claims"][
        "terse_substantively_differs_from_neutral_on_pack_grounded_definition"
    ] is True


def test_tour_convivial_substantively_differs_from_neutral():
    """ADR-0077 (R6) — same shape applied to convivial_v1."""
    report = run_tour(emit_json=True)
    assert report["claims"][
        "convivial_substantively_differs_from_neutral_on_pack_grounded_definition"
    ] is True


def test_tour_register_canonical_surfaces_identical():
    """ADR-0077 (R6) — invariant_register_canonical_surface_constant
    _across_registers.  The composer-output truth path must not move
    with the register."""
    report = run_tour(emit_json=True)
    assert report["claims"]["register_canonical_surfaces_identical"] is True


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
