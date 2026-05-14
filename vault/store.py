"""
VaultStore — exact memory via CGA inner product scan.

No HNSW. No approximate nearest neighbor. No index rebuild.
Recall is exact: argmax_i { cga_inner(query, X_i) } over stored versors.
Periodic null_project() prevents floating-point null-cone drift in long sessions.

Hot path: recall() routes through algebra.backend.vault_recall(), which
dispatches to a Rayon parallel scan (releases GIL) when core_rs is available
and falls back to a sequential Python scan silently. Public result shape
is unchanged: list of {versor, score, metadata, index}.

null_project() remains on algebra.cga — it is not the recall hot path
and does not benefit from the same batching pattern.
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

        Routes through algebra.backend.vault_recall():
          Rust path  — Rayon parallel scan, GIL released.
          Python path — sequential, behaviorally identical.
        """
        if not self._versors:
            return []

        ranked = vault_recall(self._versors, query, top_k)

        return [
            {
                "versor": self._versors[i],
                "score": float(score),
                "metadata": self._metadata[i],
                "index": i,
            }
            for i, score in ranked
        ]

    def reproject(self) -> None:
        """
        Re-project all stored versors onto the null cone.
        Corrects floating-point drift. Run between turns or asynchronously.
        null_project stays on algebra.cga — not the recall hot path.
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
