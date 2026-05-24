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
from algebra.backend import vault_recall, vault_recall_batch
from algebra.cga import null_project
from teaching.epistemic import ADMISSIBLE_AS_EVIDENCE, EpistemicStatus


def _versor_key(F: np.ndarray) -> bytes:
    return np.asarray(F, dtype=np.float32).tobytes()


def _status_admits(entry_status: EpistemicStatus, min_status: EpistemicStatus) -> bool:
    """Return True iff `entry_status` is admissible at the `min_status` tier.

    FALSIFIED entries are never admissible as evidence regardless of the
    requested tier — they carry CONTRADICTED semantics and are retained only
    for provenance and Stage-3 inversion (ADR-0021 §3).  SPECULATIVE entries
    are separately excluded at the COHERENT tier (UNVERIFIED-POSSIBLE semantics
    — not yet coherent, but distinct from actively falsified).  If the
    admissibility set grows in the future (it should not, per ADR-0021), only
    this helper changes.
    """
    if entry_status is EpistemicStatus.FALSIFIED:
        return False  # CONTRADICTED — never evidence regardless of requested tier
    if min_status is EpistemicStatus.COHERENT:
        return entry_status in ADMISSIBLE_AS_EVIDENCE
    return entry_status is min_status


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
        # ADR-0054: cached (N, D) f32 matrix view of the deque, rebuilt
        # lazily on the first recall after any mutation. Indexing
        # optimisation only — scoring arithmetic is unchanged.
        self._matrix_cache: np.ndarray | None = None

    def store(
        self,
        F: np.ndarray,
        metadata: dict | None = None,
        *,
        epistemic_status: EpistemicStatus = EpistemicStatus.SPECULATIVE,
    ) -> int:
        """Store a versor. Returns its index. Auto-reprojects every N stores.

        Every stored entry carries an EpistemicStatus stamped into its
        metadata under the ``epistemic_status`` key.  The default is
        SPECULATIVE — the safe choice per ADR-0021 §3: when in doubt,
        the entry is not admissible as evidence.  Callers that have
        actually performed a coherence judgment must declare it
        (``epistemic_status=EpistemicStatus.COHERENT``); pack authority
        and source provenance alone are not coherence judgments.
        """
        arr = np.asarray(F, dtype=np.float32).copy()
        stamped: dict = dict(metadata) if metadata else {}
        stamped["epistemic_status"] = epistemic_status.value

        will_evict = self._max_entries is not None and len(self._versors) >= self._max_entries
        self._versors.append(arr)
        self._metadata.append(stamped)
        if will_evict:
            self._rebuild_index()
        else:
            idx = len(self._versors) - 1
            key = _versor_key(arr)
            self._exact_index.setdefault(key, []).append(idx)
        self._matrix_cache = None

        self._store_count += 1
        if self._reproject_interval > 0 and self._store_count % self._reproject_interval == 0:
            self.reproject()
        return len(self._versors) - 1

    def recall(
        self,
        query: np.ndarray,
        top_k: int = 5,
        *,
        min_status: EpistemicStatus | None = None,
    ) -> list:
        """
        Return top_k closest stored versors by CGA inner product.
        Each result: {versor, score, metadata, index}.

        When ``min_status`` is None (default), no filter is applied —
        every stored entry is eligible.  This preserves raw session
        lookup behavior: the session needs to see its own turns
        regardless of epistemic tier.

        When ``min_status`` is set, only entries whose stored
        ``epistemic_status`` is admissible at that tier are returned.
        Inference paths that treat vault hits as *evidence* should pass
        ``min_status=EpistemicStatus.COHERENT`` so SPECULATIVE,
        CONTESTED, and FALSIFIED entries do not silently influence
        downstream reasoning (ADR-0021 §3).
        """
        if not self._versors or top_k <= 0:
            return []

        query_arr = np.asarray(query, dtype=np.float32)
        # Over-fetch when filtering so the post-filter result still
        # has a chance at top_k entries. 4x is a generous heuristic;
        # vault sizes are bounded by max_entries anyway.
        scan_k = max(top_k * 4, top_k) if min_status is not None else max(top_k, 1)
        matrix = self._get_matrix()
        ranked = vault_recall(
            list(self._versors), query_arr, scan_k,
            prebuilt_matrix=matrix,
        )

        key = _versor_key(query_arr)
        exact_indices = self._exact_index.get(key, [])
        if exact_indices:
            exact_matches = [(i, float("inf")) for i in exact_indices]
            seen = set(exact_indices)
            ranked = exact_matches + [(i, score) for i, score in ranked if i not in seen]

        if min_status is not None:
            filtered: list[tuple[int, float]] = []
            for i, score in ranked:
                raw_status = self._metadata[i].get("epistemic_status", "speculative")
                try:
                    entry_status = EpistemicStatus(raw_status)
                except ValueError:
                    entry_status = EpistemicStatus.SPECULATIVE
                if _status_admits(entry_status, min_status):
                    filtered.append((i, score))
            ranked = filtered

        return [
            {
                "versor": self._versors[i],
                "score": float(score),
                "metadata": self._metadata[i],
                "index": i,
            }
            for i, score in ranked[:top_k]
        ]

    def recall_batch(
        self,
        queries: np.ndarray,
        top_k: int = 5,
        *,
        min_status: EpistemicStatus | None = None,
    ) -> list[list[dict]]:
        """Recall B queries against the stored versors in one sweep.

        Returns one ``list[dict]`` per query in the same shape ``recall``
        returns.  Exact-self-match promotion, ``min_status`` filtering,
        and the descending-score / ascending-index tiebreak rule are
        applied per query — semantics are identical to looping
        ``recall(q, top_k=...)`` over each query, but the underlying
        scoring scan is a single component-serial sweep over the
        cached matrix.  ADR-0054.
        """
        Q = np.asarray(queries, dtype=np.float32)
        if Q.ndim == 1:
            Q = Q[None, :]
        if not self._versors or top_k <= 0:
            return [[] for _ in range(Q.shape[0])]

        matrix = self._get_matrix()
        assert matrix is not None  # non-empty deque ⇒ matrix is built
        scan_k = max(top_k * 4, top_k) if min_status is not None else max(top_k, 1)
        batch_ranked = vault_recall_batch(matrix, Q, scan_k)

        results: list[list[dict]] = []
        for b, ranked in enumerate(batch_ranked):
            key = _versor_key(Q[b])
            exact_indices = self._exact_index.get(key, [])
            if exact_indices:
                exact_matches = [(i, float("inf")) for i in exact_indices]
                seen = set(exact_indices)
                ranked = exact_matches + [
                    (i, score) for i, score in ranked if i not in seen
                ]

            if min_status is not None:
                filtered: list[tuple[int, float]] = []
                for i, score in ranked:
                    raw_status = self._metadata[i].get(
                        "epistemic_status", "speculative",
                    )
                    try:
                        entry_status = EpistemicStatus(raw_status)
                    except ValueError:
                        entry_status = EpistemicStatus.SPECULATIVE
                    if _status_admits(entry_status, min_status):
                        filtered.append((i, score))
                ranked = filtered

            results.append([
                {
                    "versor": self._versors[i],
                    "score": float(score),
                    "metadata": self._metadata[i],
                    "index": i,
                }
                for i, score in ranked[:top_k]
            ])
        return results

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
        self._matrix_cache = None

    def _get_matrix(self) -> np.ndarray | None:
        """Return the cached (N, D) f32 stack of stored versors.

        Rebuilds the cache on first call after any mutation.  Returns
        None when the vault is empty so callers can branch without
        constructing a 0-row array.  ADR-0054.
        """
        if not self._versors:
            return None
        if self._matrix_cache is None:
            self._matrix_cache = np.asarray(self._versors, dtype=np.float32)
        return self._matrix_cache

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
