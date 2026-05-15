"""Tests for VaultStore exact-match index and optional bounded mode."""

from __future__ import annotations

import numpy as np
from algebra.cga import embed_point
from vault.store import VaultStore, _versor_key


def _random_point(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return embed_point(rng.standard_normal(3).astype(np.float32))


def test_vault_exact_self_match_uses_index():
    """Exact self-match must come from the hash index, not O(N) scan."""
    vault = VaultStore()
    points = [_random_point(i) for i in range(20)]
    for i, v in enumerate(points):
        vault.store(v, {"id": i})

    for i, v in enumerate(points):
        key = _versor_key(v)
        assert key in vault._exact_index
        assert i in vault._exact_index[key]

    for i, v in enumerate(points):
        results = vault.recall(v, top_k=1)
        assert results[0]["metadata"]["id"] == i


def test_vault_recall_ranking_unchanged():
    """CGA inner-product ranking must be identical to pre-index behavior."""
    vault = VaultStore()
    points = [_random_point(i) for i in range(10)]
    for i, v in enumerate(points):
        vault.store(v, {"id": i})

    query = _random_point(99)
    results = vault.recall(query, top_k=5)
    assert len(results) == 5
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_vault_index_updates_on_store():
    """Each store() must update the hash index."""
    vault = VaultStore()
    p = _random_point(0)
    vault.store(p, {"id": "a"})
    key = _versor_key(p)
    assert key in vault._exact_index
    assert vault._exact_index[key] == [0]

    vault.store(p, {"id": "b"})
    assert vault._exact_index[key] == [0, 1]


def test_vault_index_rebuilds_on_reproject():
    """Reproject changes versor bytes; index must be rebuilt."""
    vault = VaultStore()
    for i in range(5):
        vault.store(_random_point(i))
    vault.reproject()
    assert len(vault._exact_index) == 5
    assert len(vault) == 5


def test_vault_optional_max_entries_eviction_is_deterministic():
    """Bounded vault must evict oldest first (FIFO), deterministically."""
    vault = VaultStore(max_entries=3)
    ids = []
    for i in range(5):
        vault.store(_random_point(i), {"id": i})
        ids.append(i)

    assert len(vault) == 3
    remaining_ids = [m["id"] for m in vault._metadata]
    assert remaining_ids == [2, 3, 4]


def test_vault_default_remains_unbounded():
    """Default max_entries=None means no eviction ever."""
    vault = VaultStore()
    assert vault.max_entries is None
    for i in range(100):
        vault.store(_random_point(i))
    assert len(vault) == 100


def test_vault_eviction_preserves_index_consistency():
    """After eviction, the exact index must reference valid current indices."""
    vault = VaultStore(max_entries=3)
    for i in range(5):
        vault.store(_random_point(i), {"id": i})

    for indices in vault._exact_index.values():
        for idx in indices:
            assert 0 <= idx < len(vault)


def test_vault_duplicate_versors_both_indexed():
    """Storing the same versor twice should index both entries."""
    vault = VaultStore()
    p = _random_point(42)
    vault.store(p, {"id": "first"})
    vault.store(p, {"id": "second"})

    results = vault.recall(p, top_k=2)
    result_ids = {r["metadata"]["id"] for r in results}
    assert result_ids == {"first", "second"}
