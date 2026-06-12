"""Tests for ADR-0148 — VaultPromotionPolicy wired into the turn boundary.

Six tests cover:
  1. Flag-off: no promotion fires (null-drop invariant).
  2. Direct promote_eligible_entries: E0/low-residual entry becomes COHERENT.
  3. Active-energy entry (E3) is not promoted (vault_candidate=False).
  4. E0 entry with high coherence_residual is not promoted.
  5. promote_eligible_entries returns correct count.
  6. finalize_turn persists energy_raw / energy_class / coherence_residual in vault metadata.
"""

from __future__ import annotations

import numpy as np
import pytest

from algebra.cga import embed_point
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from core.physics.energy import EnergyClass, EnergyProfile
from core.physics.learning import VaultPromotionPolicy
from teaching.epistemic import EpistemicStatus
from vault.store import VaultStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_versor(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return embed_point(rng.standard_normal(3).astype(np.float32))


def _store_entry(
    vault: VaultStore,
    seed: int,
    *,
    energy_class: EnergyClass,
    coherence_residual: float,
    raw: float = 0.05,
) -> None:
    """Store a SPECULATIVE entry with explicit energy metadata."""
    vault.store(
        _random_versor(seed),
        {
            "turn": seed,
            "role": "assistant",
            "energy_raw": float(raw),
            "energy_class": energy_class.value,
            "coherence_residual": float(coherence_residual),
        },
        epistemic_status=EpistemicStatus.SPECULATIVE,
    )


# ---------------------------------------------------------------------------
# Test 1 — flag-off: no promotion when vault_promotion_enabled=False
# ---------------------------------------------------------------------------

def test_speculative_entry_not_promoted_when_flag_off() -> None:
    """Vault entries remain SPECULATIVE when vault_promotion_enabled=False (default)."""
    runtime = ChatRuntime(
        config=RuntimeConfig(
            vault_promotion_enabled=False,
            output_language="en",
            frame_pack="en",
        )
    )

    for text in ("word truth", "light word", "begin truth"):
        runtime.chat(text)

    vault = runtime.session.vault
    assert len(vault) > 0, "Vault must have entries after chat turns"

    statuses = [m.get("epistemic_status") for m in vault._metadata]
    assert all(s == EpistemicStatus.SPECULATIVE.value for s in statuses), (
        "All entries should stay SPECULATIVE when vault_promotion_enabled=False"
    )


# ---------------------------------------------------------------------------
# Test 2 — promote_eligible_entries promotes E0/low-residual entry to COHERENT
# ---------------------------------------------------------------------------

def test_promote_eligible_entries_promotes_coherent_entry() -> None:
    """An E0 entry with coherence_residual=0.02 should be promoted to COHERENT."""
    vault = VaultStore()
    policy = VaultPromotionPolicy(residual_threshold=0.05)

    _store_entry(vault, seed=1, energy_class=EnergyClass.E0, coherence_residual=0.02, raw=0.05)

    count = vault.promote_eligible_entries(policy)

    assert count == 1, "Expected exactly 1 promotion"
    assert vault._metadata[0]["epistemic_status"] == EpistemicStatus.COHERENT.value, (
        "Entry should be promoted to COHERENT"
    )
    # Consistency fix shipped with ADR-0218 PR C: the stored state tag is
    # updated alongside the status, so the stamped pair never goes stale.
    assert vault._metadata[0]["epistemic_state"] == "decoded"


# ---------------------------------------------------------------------------
# Test 3 — active-energy entry (E3) is NOT promoted
# ---------------------------------------------------------------------------

def test_promote_eligible_entries_skips_active_energy() -> None:
    """An E3 entry (vault_candidate=False) must not be promoted."""
    vault = VaultStore()
    policy = VaultPromotionPolicy(residual_threshold=0.05)

    _store_entry(vault, seed=2, energy_class=EnergyClass.E3, coherence_residual=0.01, raw=0.70)

    count = vault.promote_eligible_entries(policy)

    assert count == 0, "E3 entry must not be promoted (region still active)"
    assert vault._metadata[0]["epistemic_status"] == EpistemicStatus.SPECULATIVE.value


# ---------------------------------------------------------------------------
# Test 4 — E0 entry with high coherence_residual is NOT promoted
# ---------------------------------------------------------------------------

def test_promote_eligible_entries_skips_high_residual() -> None:
    """An E0 entry with coherence_residual=0.10 must not be promoted (above threshold=0.05)."""
    vault = VaultStore()
    policy = VaultPromotionPolicy(residual_threshold=0.05)

    _store_entry(vault, seed=3, energy_class=EnergyClass.E0, coherence_residual=0.10, raw=0.05)

    count = vault.promote_eligible_entries(policy)

    assert count == 0, "High-residual E0 entry must not be promoted"
    assert vault._metadata[0]["epistemic_status"] == EpistemicStatus.SPECULATIVE.value


# ---------------------------------------------------------------------------
# Test 5 — promote_eligible_entries returns correct count
# ---------------------------------------------------------------------------

def test_promotion_count_returned() -> None:
    """promote_eligible_entries returns the number of entries actually promoted."""
    vault = VaultStore()
    policy = VaultPromotionPolicy(residual_threshold=0.05)

    # 2 promotable (E0, low residual)
    _store_entry(vault, seed=10, energy_class=EnergyClass.E0, coherence_residual=0.01, raw=0.05)
    _store_entry(vault, seed=11, energy_class=EnergyClass.E1, coherence_residual=0.03, raw=0.18)
    # 1 NOT promotable (E3)
    _store_entry(vault, seed=12, energy_class=EnergyClass.E3, coherence_residual=0.00, raw=0.70)
    # 1 NOT promotable (E0 but high residual)
    _store_entry(vault, seed=13, energy_class=EnergyClass.E0, coherence_residual=0.08, raw=0.05)

    count = vault.promote_eligible_entries(policy)

    assert count == 2, f"Expected 2 promotions, got {count}"


# ---------------------------------------------------------------------------
# Test 6 — energy stored in vault metadata after finalize_turn
# ---------------------------------------------------------------------------

def test_energy_stored_in_vault_metadata() -> None:
    """After a finalize_turn call, vault metadata contains energy_raw, energy_class,
    and coherence_residual for the assistant turn entry."""
    runtime = ChatRuntime(
        config=RuntimeConfig(
            vault_promotion_enabled=False,
            output_language="en",
            frame_pack="en",
        )
    )

    runtime.chat("light truth word")

    vault = runtime.session.vault
    assert len(vault) >= 1, "Vault must have at least one entry after a chat turn"

    # Find assistant turn entries (role=="assistant"); they carry energy metadata
    # when oriented_state.energy is not None.
    assistant_entries = [
        m for m in vault._metadata if m.get("role") == "assistant"
    ]
    assert assistant_entries, "Expected at least one assistant entry in vault"

    # At least one assistant entry should carry energy metadata.
    # (If oriented_state.energy is None for all entries, the test would fail,
    #  which would correctly surface a gap in energy propagation.)
    entries_with_energy = [
        m for m in assistant_entries
        if "energy_raw" in m and "energy_class" in m and "coherence_residual" in m
    ]
    assert entries_with_energy, (
        "Expected at least one assistant vault entry to carry energy metadata "
        "(energy_raw, energy_class, coherence_residual)"
    )

    for m in entries_with_energy:
        assert isinstance(m["energy_raw"], float), "energy_raw must be a float"
        assert isinstance(m["energy_class"], str), "energy_class must be a string"
        # Verify the energy_class value is a valid EnergyClass member
        EnergyClass(m["energy_class"])  # raises ValueError if invalid
        assert isinstance(m["coherence_residual"], float), "coherence_residual must be a float"
        assert 0.0 <= m["coherence_residual"] <= 1.0, (
            f"coherence_residual out of range: {m['coherence_residual']}"
        )
