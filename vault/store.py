"""
VaultStore — exact memory via CGA inner product scan.

No HNSW. No approximate nearest neighbor. No index rebuild.
Recall is exact: argmax_i { cga_inner(query, X_i) } over stored versors.
Periodic null_project() prevents floating-point null-cone drift in long sessions.
"""

import numpy as np
from algebra.cga import cga_inner, null_project


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
        if self._store_count % self._reproject_interval == 0:
            self.reproject()
        return len(self._versors) - 1

    def recall(self, query: np.ndarray, top_k: int = 5) -> list:
        """
        Return top_k closest stored versors by CGA inner product.
        Each result: {versor, score, metadata, index}
        """
        if not self._versors:
            return []
        scores = [cga_inner(query, v) for v in self._versors]
        top_indices = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
        return [
            {
                "versor": self._versors[i],
                "score": scores[i],
                "metadata": self._metadata[i],
                "index": i,
            }
            for i in top_indices
        ]

    def reproject(self) -> None:
        """
        Re-project all stored versors onto the null cone.
        Corrects floating-point drift. Run between turns or asynchronously.
        """
        self._versors = [null_project(v) for v in self._versors]

    def __len__(self) -> int:
        return len(self._versors)
