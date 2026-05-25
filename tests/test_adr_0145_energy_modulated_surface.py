"""Tests for ADR-0145: Energy-Modulated Vault Surface Readback.

Pins:
  - energy_modulated_surface() prefix table (pure-function contract)
  - empty-base passthrough (no prefix added to empty strings)
  - recall_energy_class is None on non-vault-grounded responses
  - recall_energy_class is populated and surface is prefixed on vault hits
"""

from __future__ import annotations

from chat.runtime import ChatRuntime
from core.physics.energy import EnergyClass
from generate.realizer import energy_modulated_surface


def test_e2_prepends_recall_prefix() -> None:
    assert energy_modulated_surface("Light is coherence.", EnergyClass.E2) == (
        "I recall: Light is coherence."
    )


def test_e0_prepends_from_memory() -> None:
    assert energy_modulated_surface("Truth is settled.", EnergyClass.E0) == (
        "From memory: Truth is settled."
    )


def test_e1_prepends_seem_to_recall() -> None:
    assert energy_modulated_surface("Memory persists.", EnergyClass.E1) == (
        "I seem to recall: Memory persists."
    )


def test_e3_no_prefix() -> None:
    assert energy_modulated_surface("Clarity.", EnergyClass.E3) == "Clarity."


def test_e4_no_prefix() -> None:
    assert energy_modulated_surface("Boundary.", EnergyClass.E4) == "Boundary."


def test_empty_base_unchanged_e2() -> None:
    assert energy_modulated_surface("", EnergyClass.E2) == ""


def test_empty_base_unchanged_e0() -> None:
    assert energy_modulated_surface("", EnergyClass.E0) == ""


def test_pack_grounded_has_no_recall_class() -> None:
    """Pack-grounded responses must not carry recall_energy_class."""
    rt = ChatRuntime()
    resp = rt.chat("What is light?")
    assert resp.grounding_source in {"pack", "teaching", "none"}
    assert resp.recall_energy_class is None


def test_vault_grounded_surface_has_recall_prefix() -> None:
    """When a turn gets a vault hit the surface starts with the E2 recall
    prefix and recall_energy_class is populated.  If the gate doesn't fire
    on this call (non-deterministic in general) the assertions apply only
    when grounding_source is vault."""
    rt = ChatRuntime()
    rt.chat("light truth")
    resp = rt.chat("light truth")
    if resp.grounding_source == "vault":
        assert resp.recall_energy_class == "E2"
        assert resp.surface.startswith("I recall: ")
    else:
        assert resp.recall_energy_class is None
