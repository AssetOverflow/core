"""
VaultStore — exact memory via CGA inner product scan.

No HNSW. No approximate nearest neighbor. No index rebuild.
Recall is exact and deterministic over stored versors. When the query is the
same point that was stored, exact self-match is promoted ahead of metric ties
or CGA-sign artifacts.
"""

import numpy as np
from algebra.backend import vault_recall
from algebra.cga import null_project


class VaultStore:
    def __init__(self, reproject_interval: int = 100):
        self._versors: list = []
        self._metadata: list = []
        self._store_count: int = 0
        self._reproject_interval = reproject_interval

    def store(self, F: np.ndarray, metadata: dict = None) -> int:
        """Store a versor. Returns its index. Auto-reprojects every N stores."""
        self._versors.append(np.asarray(F, dtype=np.float32).copy())
        self._metadata.append(metadata or {})
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
        ranked = vault_recall(self._versors, query_arr, max(top_k, 1))

        exact_matches = [
            (i, float("inf"))
            for i, versor in enumerate(self._versors)
            if np.array_equal(np.asarray(versor, dtype=np.float32), query_arr)
        ]
        if exact_matches:
            seen = {i for i, _score in exact_matches}
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
        self._versors = [null_project(v) for v in self._versors]

    @property
    def reproject_interval(self) -> int:
        """Return the configured auto-reprojection cadence in store operations."""
        return self._reproject_interval

    @property
    def store_count(self) -> int:
        """Return how many store() operations have occurred in this vault."""
        return self._store_count

    def __len__(self) -> int:
        return len(self._versors)
