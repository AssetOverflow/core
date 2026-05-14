import numpy as np
import pytest

from algebra.cga import embed_point, is_null
from vault.store import VaultStore


def _random_point(seed=0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return embed_point(rng.standard_normal(3).astype(np.float32))


def test_store_and_recall_top1():
    """Each stored point should recall itself as the top result."""
    vault = VaultStore()
    points = [_random_point(i) for i in range(20)]
    for i, v in enumerate(points):
        vault.store(v, {"id": i})
    for i, v in enumerate(points):
        results = vault.recall(v, top_k=1)
        assert results[0]["metadata"]["id"] == i, (
            f"Point {i} did not recall itself as top result"
        )


def test_recall_empty_vault():
    vault = VaultStore()
    result = vault.recall(_random_point(), top_k=5)
    assert result == []


def test_reproject_maintains_structure():
    """Reproject should not lose stored entries."""
    vault = VaultStore()
    for i in range(10):
        vault.store(_random_point(i), {"id": i})
    vault.reproject()
    assert len(vault) == 10


def test_vault_len():
    vault = VaultStore()
    for i in range(5):
        vault.store(_random_point(i))
    assert len(vault) == 5

