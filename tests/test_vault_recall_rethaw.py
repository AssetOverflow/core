"""Tests for ADR-0006 vault-recall re-thaw (W-004).

ADR-0006 §"Integration Points": "Vault recall re-activates the region to E2
transiently, then lets it cool again."

These tests pin the contract that vault.recall and vault.recall_batch return
an EnergyProfile with energy_class=E2 on every returned entry, declaring
the transient re-activation.
"""

from __future__ import annotations

import numpy as np

from core.physics.energy import EnergyClass, EnergyProfile
from teaching.epistemic import EpistemicStatus
from vault.store import VaultStore, _VAULT_RECALL_RETHAW_ENERGY


def _make_versor(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(32).astype(np.float32)


def test_recall_returns_energy_profile_e2() -> None:
    """Every recall result carries an EnergyProfile declaring E2 re-thaw."""
    store = VaultStore()
    for i in range(3):
        store.store(_make_versor(i), {"label": f"entry-{i}"})

    results = store.recall(_make_versor(0), top_k=3)
    assert len(results) == 3
    for hit in results:
        assert "energy_profile" in hit, "recall result missing energy_profile"
        profile = hit["energy_profile"]
        assert isinstance(profile, EnergyProfile)
        assert profile.energy_class is EnergyClass.E2


def test_recall_batch_returns_energy_profile_e2() -> None:
    """Batched recall stamps the same re-thaw energy on every entry."""
    store = VaultStore()
    for i in range(3):
        store.store(_make_versor(i), {"label": f"entry-{i}"})

    queries = np.stack([_make_versor(0), _make_versor(1)])
    batch_results = store.recall_batch(queries, top_k=2)
    assert len(batch_results) == 2
    for per_query in batch_results:
        assert len(per_query) == 2
        for hit in per_query:
            assert "energy_profile" in hit
            assert hit["energy_profile"].energy_class is EnergyClass.E2


def test_rethaw_energy_singleton_byte_identical() -> None:
    """The re-thaw EnergyProfile is a deterministic singleton — no per-call
    drift. Required for replay byte-identity (same recall sequence ⇒ same
    energy profile on every entry)."""
    store = VaultStore()
    store.store(_make_versor(0), {"label": "entry-0"})

    a = store.recall(_make_versor(0), top_k=1)[0]["energy_profile"]
    b = store.recall(_make_versor(0), top_k=1)[0]["energy_profile"]
    assert a is b, "re-thaw profile must be a stable singleton, not a fresh allocation"
    assert a is _VAULT_RECALL_RETHAW_ENERGY


def test_recall_empty_vault_does_not_emit_profile() -> None:
    """Empty vault returns []; no energy_profile to attach."""
    store = VaultStore()
    assert store.recall(_make_versor(0), top_k=5) == []


def test_recall_with_min_status_still_carries_energy_profile() -> None:
    """min_status filtering does not strip the energy_profile field."""
    store = VaultStore()
    store.store(_make_versor(0), {"label": "coherent"},
                epistemic_status=EpistemicStatus.COHERENT)
    store.store(_make_versor(1), {"label": "speculative"},
                epistemic_status=EpistemicStatus.SPECULATIVE)

    results = store.recall(
        _make_versor(0), top_k=5,
        min_status=EpistemicStatus.COHERENT,
    )
    assert len(results) == 1
    assert results[0]["energy_profile"].energy_class is EnergyClass.E2


def test_rethaw_profile_raw_is_in_e2_band() -> None:
    """ADR-0006 declares E2 transient re-activation. Verify the singleton's
    raw value sits in the E2 band [0.37, 0.62) — so it is unambiguously E2
    rather than borderline."""
    profile = _VAULT_RECALL_RETHAW_ENERGY
    assert 0.37 <= profile.raw < 0.62
    assert profile.energy_class is EnergyClass.E2
