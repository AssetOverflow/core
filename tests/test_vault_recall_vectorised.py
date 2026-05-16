"""ADR-0019 Stage 1 — bit-identity contract for vectorised vault recall.

The vectorised path in `algebra.backend.vault_recall` must produce
results that are bit-identical to a per-versor scalar `cga_inner`
scan.  This is the load-bearing claim of Stage 1: we replaced the
per-element Python dispatch loop with a vector op, but the scoring
arithmetic is unchanged.

If this test ever starts failing, the acceleration has become
approximate — that violates CLAUDE.md.  Fix the kernel, not the
test.
"""

from __future__ import annotations

import numpy as np
import pytest

from algebra.backend import _CGA_INNER_METRIC, vault_recall
from algebra.cga import cga_inner
from algebra.cl41 import N_COMPONENTS


def _scalar_topk(versors: list[np.ndarray], query: np.ndarray, top_k: int) -> list[tuple[int, float]]:
    q = np.asarray(query, dtype=np.float32)
    scored = [(i, float(cga_inner(q, np.asarray(v, dtype=np.float32))))
              for i, v in enumerate(versors)]
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]


def test_metric_is_diagonal_pm_one() -> None:
    """The derived metric must be ±1 per component (the precondition
    for the vectorised scan to be exact)."""
    assert _CGA_INNER_METRIC.shape == (N_COMPONENTS,)
    assert _CGA_INNER_METRIC.dtype == np.float32
    assert set(_CGA_INNER_METRIC.tolist()) <= {1.0, -1.0}


@pytest.mark.parametrize("seed", [0xC07E, 0xBEEF, 0x1234, 0xFACE])
def test_vault_recall_scores_bit_identical_to_scalar(seed: int) -> None:
    rng = np.random.default_rng(seed)
    N = 137
    versors = [rng.standard_normal(size=(32,), dtype=np.float32) for _ in range(N)]
    query = rng.standard_normal(size=(32,), dtype=np.float32)

    expected = _scalar_topk(versors, query, top_k=N)
    actual = vault_recall(versors, query, top_k=N)

    assert len(actual) == len(expected) == N

    actual_scores = np.array([s for _, s in actual], dtype=np.float32)
    expected_scores = np.array([s for _, s in expected], dtype=np.float32)
    assert np.array_equal(actual_scores, expected_scores), (
        "Vectorised recall scores must be bit-identical to scalar path."
    )

    actual_ids = [i for i, _ in actual]
    expected_ids = [i for i, _ in expected]
    assert actual_ids == expected_ids, (
        "Top-k ordering must match scalar path (descending score, ascending index on ties)."
    )


def test_vault_recall_top_k_smaller_than_n() -> None:
    rng = np.random.default_rng(0xDEAD)
    versors = [rng.standard_normal(size=(32,), dtype=np.float32) for _ in range(200)]
    query = rng.standard_normal(size=(32,), dtype=np.float32)

    expected = _scalar_topk(versors, query, top_k=5)
    actual = vault_recall(versors, query, top_k=5)
    assert actual == expected


def test_vault_recall_empty() -> None:
    rng = np.random.default_rng(0)
    query = rng.standard_normal(size=(32,), dtype=np.float32)
    assert vault_recall([], query, top_k=5) == []


def test_vault_recall_tie_break_is_stable() -> None:
    """Two versors with identical scores must order by ascending index."""
    v = np.zeros((32,), dtype=np.float32)
    v[0] = 1.0
    versors = [v, v, v]
    query = v
    out = vault_recall(versors, query, top_k=3)
    assert [i for i, _ in out] == [0, 1, 2]
