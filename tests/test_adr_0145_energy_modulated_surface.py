"""Tests for ADR-0145: Energy-Modulated Vault Surface Readback.

These tests pin the contract that surface readback is modulated by the energy
class of the grounding source. In particular, vault-grounded turns should prepended
with energy-dependent prefixes, and the recall energy class must be threaded to
ChatResponse.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime, ChatResponse
from core.physics.energy import EnergyClass
from generate.realizer import energy_modulated_surface


def test_energy_modulated_surface_e2_prepends_recall_prefix() -> None:
    assert (
        energy_modulated_surface("Light is coherence.", EnergyClass.E2)
        == "I recall: Light is coherence."
    )


def test_energy_modulated_surface_e0_prepends_from_memory() -> None:
    assert (
        energy_modulated_surface("Truth is settled.", EnergyClass.E0)
        == "From memory: Truth is settled."
    )


def test_energy_modulated_surface_e1_prepends_seem_to_recall() -> None:
    result = energy_modulated_surface("Light is coherence.", EnergyClass.E1)
    assert result.startswith("I seem to recall: ")
    assert result == "I seem to recall: Light is coherence."


def test_energy_modulated_surface_e3_no_prefix() -> None:
    assert (
        energy_modulated_surface("Clarity.", EnergyClass.E3)
        == "Clarity."
    )


def test_energy_modulated_surface_empty_base_unchanged() -> None:
    assert energy_modulated_surface("", EnergyClass.E2) == ""


def test_vault_grounded_response_has_recall_prefix() -> None:
    runtime = ChatRuntime()
    # Establish a turn state
    runtime.chat("logos arche")
    
    # Store the turn manually in the session vault
    runtime.session.vault.store(runtime.session.state.F, metadata={"role": "assistant"})
    
    # Recall the turn
    response = runtime.chat("logos arche")
    
    assert response.grounding_source == "vault"
    assert response.surface.startswith("I recall: ")
    assert response.recall_energy_class == "E2"


def test_pack_grounded_response_has_no_recall_prefix() -> None:
    runtime = ChatRuntime()
    response = runtime.chat("What is truth?")
    
    assert response.grounding_source in {"pack", "teaching"}
    assert not response.surface.startswith("I recall: ")
    assert response.recall_energy_class is None


def test_recall_energy_class_is_e2_on_vault_hit() -> None:
    runtime = ChatRuntime()
    runtime.chat("logos arche")
    runtime.session.vault.store(runtime.session.state.F, metadata={"role": "assistant"})
    response = runtime.chat("logos arche")
    
    assert response.recall_energy_class == "E2"
