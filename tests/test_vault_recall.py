import numpy as np
import pytest

from algebra.versor import unitize_versor
from algebra.cga import is_null
from vault.store import VaultStore


def _random_versor(seed=0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return unitize_versor(rng.standard_normal(32).astype(np.float32))


def test_store_and_recall_top1():
    """Each stored versor should recall itself as the top result."""
    vault = VaultStore()
    versors = [_random_versor(i) for i in range(20)]
    for i, v in enumerate(versors):
        vault.store(v, {"id": i})
    for i, v in enumerate(versors):
        results = vault.recall(v, top_k=1)
        assert results[0]["metadata"]["id"] == i, (
            f"Versor {i} did not recall itself as top result"
        )


def test_recall_empty_vault():
    vault = VaultStore()
    result = vault.recall(_random_versor(), top_k=5)
    assert result == []


def test_reproject_maintains_structure():
    """Reproject should not lose stored entries."""
    vault = VaultStore()
    for i in range(10):
        vault.store(_random_versor(i), {"id": i})
    vault.reproject()
    assert len(vault) == 10


def test_vault_len():
    vault = VaultStore()
    for i in range(5):
        vault.store(_random_versor(i))
    assert len(vault) == 5
