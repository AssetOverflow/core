"""
VaultStore — exact memory via CGA inner product scan.

No HNSW. No approximate nearest neighbor. No index rebuild.
Recall is exact and deterministic over stored versors. When the query is the
same point that was stored, exact self-match is promoted ahead of metric ties
or CGA-sign artifacts.

Exact self-match uses a hash index (versor bytes -> stored indices) instead of
O(N) np.array_equal scans.
"""

from __future__ import annotations

from collections import deque

import numpy as np
from algebra.backend import vault_recall
from algebra.cga import null_project


def _versor_key(F: np.ndarray) -> bytes:
    return np.asarray(F, dtype=np.float32).tobytes()


class VaultStore:
    def __init__(
        self,
        reproject_interval: int = 100,
        max_entries: int | None = None,
    ):
        self._versors: deque[np.ndarray] = deque(maxlen=max_entries)
        self._metadata: deque[dict] = deque(maxlen=max_entries)
        self._store_count: int = 0
        self._reproject_interval = reproject_interval
        self._max_entries = max_entries
        self._exact_index: dict[bytes, list[int]] = {}

    def store(self, F: np.ndarray, metadata: dict | None = None) -> int:
        """Store a versor. Returns its index. Auto-reprojects every N stores."""
        arr = np.asarray(F, dtype=np.float32).copy()

        will_evict = self._max_entries is not None and len(self._versors) >= self._max_entries
        self._versors.append(arr)
        self._metadata.append(metadata or {})
        if will_evict:
            self._rebuild_index()
        else:
            idx = len(self._versors) - 1
            key = _versor_key(arr)
            self._exact_index.setdefault(key, []).append(idx)

        self._store_count += 1
        if self._reproject_interval > 0 and self._store_count % self._reproject_interval == 0:
            self.reproject()
        return len(self._versors) - 1

    def recall(self, query: np.ndarray, top_k: int = 5) -> list:
        """
        Return top_k closest stored versors by CGA inner product.
        Each result: {versor, score, metadata, index}
        """
        if not self._versors or top_k <= 0:
            return []

        query_arr = np.asarray(query, dtype=np.float32)
        ranked = vault_recall(list(self._versors), query_arr, max(top_k, 1))

        key = _versor_key(query_arr)
        exact_indices = self._exact_index.get(key, [])
        if exact_indices:
            exact_matches = [(i, float("inf")) for i in exact_indices]
            seen = set(exact_indices)
            ranked = exact_matches + [(i, score) for i, score in ranked if i not in seen]

        return [
            {
                "versor": self._versors[i],
                "score": float(score),
                "metadata": self._metadata[i],
                "index": i,
            }
            for i, score in ranked[:top_k]
        ]

    def reproject(self) -> None:
        """
        Re-project all stored versors onto the null cone.
        Corrects floating-point drift. Run between turns or asynchronously.
        """
        reprojected = deque((null_project(v) for v in self._versors), maxlen=self._max_entries)
        self._versors = reprojected
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._exact_index = {}
        for i, v in enumerate(self._versors):
            key = _versor_key(v)
            self._exact_index.setdefault(key, []).append(i)

    @property
    def reproject_interval(self) -> int:
        return self._reproject_interval

    @property
    def store_count(self) -> int:
        return self._store_count

    @property
    def max_entries(self) -> int | None:
        return self._max_entries

    def __len__(self) -> int:
        return len(self._versors)
