"""ADR-0054 — vault recall indexing + batched API.

Two doctrine-aligned optimisations on top of ADR-0019 Stage 1:

  1. **Indexing**: ``VaultStore`` keeps a cached ``(N, D)`` f32 matrix
     view of the deque, rebuilt lazily on the first recall after any
     mutation.  Repeated recalls reuse the cached matrix instead of
     rebuilding it from a Python list each call.

  2. **Batching**: ``algebra.backend.vault_recall_batch`` scores B
     queries against one matrix in a single component-serial sweep —
     bit-identical per-query to ``vault_recall``.

No approximate search.  No hot-path repair.  No mutation of shared
cached state during recall.  ``versor_condition < 1e-6`` invariant is
not touched by either change.
"""

from __future__ import annotations

import numpy as np
import pytest

from algebra.backend import vault_recall, vault_recall_batch
from teaching.epistemic import EpistemicStatus
from vault.store import VaultStore


# ---------------------------------------------------------------------------
# vault_recall_batch — bit-identity vs single-query vault_recall
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234])
def test_batch_matches_per_query_bit_identical(seed: int) -> None:
    rng = np.random.default_rng(seed)
    N, B = 137, 7
    versors = [rng.standard_normal(size=(32,), dtype=np.float32) for _ in range(N)]
    queries = rng.standard_normal(size=(B, 32), dtype=np.float32)
    matrix = np.asarray(versors, dtype=np.float32)

    batch = vault_recall_batch(matrix, queries, top_k=N)
    per_query = [vault_recall(versors, queries[b], top_k=N) for b in range(B)]

    assert len(batch) == B == len(per_query)
    for b in range(B):
        # Indices must be identical.
        assert [i for i, _ in batch[b]] == [i for i, _ in per_query[b]]
        # Scores must be float-equal (bit-identical at f32).
        b_scores = np.array([s for _, s in batch[b]], dtype=np.float32)
        q_scores = np.array([s for _, s in per_query[b]], dtype=np.float32)
        assert np.array_equal(b_scores, q_scores)


def test_batch_handles_1d_query() -> None:
    rng = np.random.default_rng(0)
    versors = [rng.standard_normal(size=(32,), dtype=np.float32) for _ in range(10)]
    matrix = np.asarray(versors, dtype=np.float32)
    q = rng.standard_normal(size=(32,), dtype=np.float32)
    batch = vault_recall_batch(matrix, q, top_k=3)
    assert len(batch) == 1
    expected = vault_recall(versors, q, top_k=3)
    assert batch[0] == expected


def test_batch_empty_matrix_returns_empty_per_query() -> None:
    M = np.zeros((0, 32), dtype=np.float32)
    Q = np.zeros((3, 32), dtype=np.float32)
    out = vault_recall_batch(M, Q, top_k=5)
    assert out == [[], [], []]


def test_batch_zero_top_k_returns_empty_per_query() -> None:
    rng = np.random.default_rng(0)
    M = rng.standard_normal(size=(10, 32), dtype=np.float32)
    Q = rng.standard_normal(size=(2, 32), dtype=np.float32)
    out = vault_recall_batch(M, Q, top_k=0)
    assert out == [[], []]


def test_batch_shape_mismatch_raises() -> None:
    M = np.zeros((5, 32), dtype=np.float32)
    Q = np.zeros((2, 31), dtype=np.float32)
    with pytest.raises(ValueError) as excinfo:
        vault_recall_batch(M, Q, top_k=3)
    assert "components" in str(excinfo.value)


def test_batch_rejects_higher_dim_matrix() -> None:
    M = np.zeros((2, 5, 32), dtype=np.float32)
    Q = np.zeros((1, 32), dtype=np.float32)
    with pytest.raises(ValueError):
        vault_recall_batch(M, Q, top_k=1)


def test_batch_top_k_smaller_than_n_preserves_ordering() -> None:
    rng = np.random.default_rng(0xDEAD)
    versors = [rng.standard_normal(size=(32,), dtype=np.float32) for _ in range(50)]
    matrix = np.asarray(versors, dtype=np.float32)
    queries = rng.standard_normal(size=(4, 32), dtype=np.float32)
    batch = vault_recall_batch(matrix, queries, top_k=5)
    for b in range(4):
        single = vault_recall(versors, queries[b], top_k=5)
        assert batch[b] == single


# ---------------------------------------------------------------------------
# VaultStore matrix cache — invalidation correctness
# ---------------------------------------------------------------------------


def _v(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(size=(32,), dtype=np.float32)


def test_matrix_cache_starts_unbuilt() -> None:
    store = VaultStore()
    assert store._matrix_cache is None


def test_matrix_cache_built_on_first_recall() -> None:
    store = VaultStore()
    store.store(_v(1))
    store.store(_v(2))
    assert store._matrix_cache is None
    store.recall(_v(3), top_k=1)
    assert store._matrix_cache is not None
    assert store._matrix_cache.shape == (2, 32)


def test_matrix_cache_invalidated_on_store() -> None:
    store = VaultStore()
    store.store(_v(1))
    store.recall(_v(2), top_k=1)
    assert store._matrix_cache is not None
    store.store(_v(3))
    assert store._matrix_cache is None


def test_matrix_cache_invalidated_on_reproject() -> None:
    store = VaultStore()
    store.store(_v(1))
    store.recall(_v(2), top_k=1)
    assert store._matrix_cache is not None
    store.reproject()
    assert store._matrix_cache is None


def test_matrix_cache_invalidated_on_eviction() -> None:
    store = VaultStore(max_entries=2)
    store.store(_v(1))
    store.store(_v(2))
    store.recall(_v(3), top_k=1)
    assert store._matrix_cache is not None
    store.store(_v(4))  # triggers eviction → _rebuild_index → invalidate
    assert store._matrix_cache is None


def test_matrix_cache_does_not_change_recall_results() -> None:
    """The cache is an indexing optimisation — results must equal the
    pre-cache recall behaviour case-for-case."""
    rng = np.random.default_rng(0xC0DE)
    store_a = VaultStore(reproject_interval=0)
    store_b = VaultStore(reproject_interval=0)
    versors = [rng.standard_normal(size=(32,), dtype=np.float32) for _ in range(20)]
    for v in versors:
        store_a.store(v)
        store_b.store(v)

    for _ in range(5):
        q = rng.standard_normal(size=(32,), dtype=np.float32)
        # Force store_a to take fresh non-cached path by clearing cache.
        store_a._matrix_cache = None
        r_a = store_a.recall(q, top_k=5)
        # store_b takes cached path on second+ recalls.
        store_b.recall(q, top_k=5)  # warm cache
        store_b._matrix_cache = store_b._get_matrix()  # ensure cache exists
        r_b = store_b.recall(q, top_k=5)
        assert [r["index"] for r in r_a] == [r["index"] for r in r_b]
        assert [r["score"] for r in r_a] == [r["score"] for r in r_b]


# ---------------------------------------------------------------------------
# VaultStore.recall_batch — parity with per-query recall
# ---------------------------------------------------------------------------


def test_recall_batch_matches_per_query_recall() -> None:
    rng = np.random.default_rng(0xFACE)
    store = VaultStore(reproject_interval=0)
    versors = [rng.standard_normal(size=(32,), dtype=np.float32) for _ in range(30)]
    for v in versors:
        store.store(v)

    queries = rng.standard_normal(size=(4, 32), dtype=np.float32)
    batch = store.recall_batch(queries, top_k=5)
    per_query = [store.recall(queries[b], top_k=5) for b in range(4)]

    assert len(batch) == 4
    for b in range(4):
        assert [r["index"] for r in batch[b]] == [r["index"] for r in per_query[b]]
        assert [r["score"] for r in batch[b]] == [r["score"] for r in per_query[b]]


def test_recall_batch_empty_vault_returns_empty_per_query() -> None:
    store = VaultStore()
    Q = np.zeros((3, 32), dtype=np.float32)
    out = store.recall_batch(Q, top_k=5)
    assert out == [[], [], []]


def test_recall_batch_zero_top_k_returns_empty_per_query() -> None:
    store = VaultStore()
    store.store(_v(1))
    Q = np.zeros((2, 32), dtype=np.float32)
    out = store.recall_batch(Q, top_k=0)
    assert out == [[], []]


def test_recall_batch_accepts_1d_query_as_single_batch() -> None:
    store = VaultStore(reproject_interval=0)
    store.store(_v(1))
    store.store(_v(2))
    out = store.recall_batch(_v(3), top_k=2)
    assert len(out) == 1
    expected = store.recall(_v(3), top_k=2)
    assert [r["index"] for r in out[0]] == [r["index"] for r in expected]


def test_recall_batch_exact_self_match_promoted() -> None:
    """If a query equals a stored versor, its index must appear first
    with score=+inf — same contract as single-query recall."""
    store = VaultStore(reproject_interval=0)
    target = _v(1)
    store.store(_v(0))
    store.store(target)
    store.store(_v(2))
    Q = np.stack([target, _v(99)])
    out = store.recall_batch(Q, top_k=3)
    assert out[0][0]["index"] == 1
    assert out[0][0]["score"] == float("inf")


def test_recall_batch_min_status_filter_applied_per_query() -> None:
    store = VaultStore(reproject_interval=0)
    store.store(_v(1), epistemic_status=EpistemicStatus.COHERENT)
    store.store(_v(2), epistemic_status=EpistemicStatus.SPECULATIVE)
    store.store(_v(3), epistemic_status=EpistemicStatus.COHERENT)
    Q = np.stack([_v(10), _v(11)])
    out = store.recall_batch(Q, top_k=5, min_status=EpistemicStatus.COHERENT)
    for per_query in out:
        for r in per_query:
            assert r["metadata"]["epistemic_status"] == "coherent"
