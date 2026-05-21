"""
Backend dispatch.

Pure Python is the deterministic default.  Rust is an explicit opt-in backend
via CORE_BACKEND=rust/core_rs.  This avoids silently bypassing Python-side
closure semantics when a local core_rs build happens to be importable.

Usage:
    from algebra.backend import geometric_product, versor_apply, cga_inner, vault_recall
"""

import os

import numpy as np

_REQUESTED_BACKEND = os.environ.get("CORE_BACKEND", "").strip().lower()
_ALLOW_RUST = _REQUESTED_BACKEND in {"rust", "core_rs", "rs"}

try:
    import core_rs as _rs
    _RUST = _ALLOW_RUST
except ImportError:
    _RUST = False


def _build_cga_inner_metric() -> np.ndarray:
    """Derive the Cl(4,1) inner-product metric vector from cga_inner.

    For Cl(p,q) basis blades, e_i * e_j is scalar only when i == j, so
    cga_inner(X, Y) reduces to a diagonal weighted dot product:
        cga_inner(X, Y) = sum_i metric[i] * X[i] * Y[i]
    where metric[i] = cga_inner(e_i, e_i) is ±1.  Computing the metric
    once at import time lets vault recall scan via vectorised NumPy
    ops while preserving the scalar path's serial reduction order
    bit-for-bit.
    """
    from algebra.cga import cga_inner as _ci
    from algebra.cl41 import N_COMPONENTS

    metric = np.zeros(N_COMPONENTS, dtype=np.float32)
    for i in range(N_COMPONENTS):
        e_i = np.zeros(N_COMPONENTS, dtype=np.float32)
        e_i[i] = 1.0
        metric[i] = _ci(e_i, e_i)
    return metric


_CGA_INNER_METRIC: np.ndarray = _build_cga_inner_metric()


def geometric_product(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    if _RUST:
        return np.asarray(_rs.geometric_product(A, B), dtype=np.float32)
    from algebra.cl41 import geometric_product as _gp
    return _gp(A, B)


def versor_apply(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Apply a versor through the canonical algebra closure boundary.

    The Python implementation is the default source of truth for runtime
    closure semantics.  The Rust f64 closure path
    (`versor_apply_with_closure_f64`) is a bit-identity port of
    `algebra.versor.versor_apply` + `_close_applied_versor`; ADR-0020
    parity gate `tests/test_versor_apply_rust_parity.py` proves the
    swap is safe before this dispatch is enabled.
    """
    if _RUST:
        try:
            Vc = np.ascontiguousarray(V, dtype=np.float64)
            Fc = np.ascontiguousarray(F, dtype=np.float64)
            return np.asarray(_rs.versor_apply_with_closure_f64(Vc, Fc), dtype=np.float64)
        except (AttributeError, Exception):
            pass
    from algebra.versor import versor_apply as _va
    return _va(V, F)


def versor_condition(F: np.ndarray) -> float:
    if _RUST:
        return float(_rs.versor_condition(F))
    from algebra.versor import versor_condition as _vc
    return _vc(F)


def cga_inner(X: np.ndarray, Y: np.ndarray) -> float:
    if _RUST:
        return float(_rs.cga_inner(X, Y))
    from algebra.cga import cga_inner as _ci
    return _ci(X, Y)


def vault_recall(
    versors: list,
    query: np.ndarray,
    top_k: int = 5,
    *,
    prebuilt_matrix: np.ndarray | None = None,
) -> list:
    """Top-k CGA inner product recall.

    Rust path: parallel Rayon scan when explicitly enabled.
    Python path: vectorised exact scan via the diagonal CGA inner-
    product metric.  Bit-identical to the scalar `cga_inner` path
    because the per-versor sum is folded in the same serial component
    order; the only thing the vectorisation replaces is the
    per-element Python dispatch loop.  ADR-0019 Stage 1.

    ``prebuilt_matrix`` (ADR-0054): optional cached (N, D) f32 matrix
    of stacked versors maintained by ``VaultStore``.  When supplied,
    the deque→ndarray conversion is skipped — purely an indexing
    optimisation, scoring arithmetic is identical.
    """
    if not versors and prebuilt_matrix is None:
        return []
    q = np.asarray(query, dtype=np.float32)
    if prebuilt_matrix is not None:
        M = prebuilt_matrix
        if M.shape[0] == 0:
            return []
    else:
        M = np.asarray(versors, dtype=np.float32)
    if _RUST and M.ndim == 2 and M.shape[1] == 32:
        try:
            # Pass the (N, 32) numpy buffer directly — the Rust
            # binding reads it zero-copy via PyReadonlyArray2 (task
            # #35).  ascontiguousarray ensures C-contiguous f32
            # layout, which the zero-copy slice requires.
            Mc = np.ascontiguousarray(M, dtype=np.float32)
            qc = np.ascontiguousarray(q, dtype=np.float32)
            return _rs.vault_recall(Mc, qc, top_k)
        except Exception:
            pass
    if M.ndim != 2:
        # Heterogeneous shapes — fall back to the scalar path rather
        # than coerce silently.
        scores_list = [(i, float(cga_inner(q, np.asarray(v)))) for i, v in enumerate(versors)]
        scores_list.sort(key=lambda x: -x[1])
        return scores_list[:top_k]
    scores = np.zeros(M.shape[0], dtype=np.float32)
    for i in range(M.shape[1]):
        scores += (_CGA_INNER_METRIC[i] * M[:, i]) * q[i]
    k = min(top_k, scores.shape[0])
    if k <= 0:
        return []
    # argpartition gives unordered top-k; finalize the order with a
    # stable sort by descending score, then ascending index for ties
    # (mirrors the scalar path's stable enumerate order under
    # list.sort with a strict key).
    if k < scores.shape[0]:
        cand = np.argpartition(-scores, k - 1)[:k]
    else:
        cand = np.arange(scores.shape[0])
    # Stable order: primary key -scores ascending (= score descending),
    # tiebreak ascending index to match scalar path's enumerate + stable
    # list.sort ordering.
    order = np.lexsort((cand, -scores[cand]))
    cand = cand[order]
    return [(int(i), float(scores[i])) for i in cand]


def vault_recall_batch(
    matrix: np.ndarray,
    queries: np.ndarray,
    top_k: int = 5,
) -> list[list[tuple[int, float]]]:
    """Top-k CGA inner product recall for B queries against one matrix.

    ADR-0054.  Returns one ``[(index, score), ...]`` list per query in
    the same shape ``vault_recall`` returns for a single query.

    Bit-identity contract: each per-query result must equal the
    corresponding single-query ``vault_recall`` call against the same
    matrix.  We accumulate scores in component-serial order with the
    diagonal metric — the same folding pattern as the single-query
    path — so the per-versor sum is folded identically.  Top-k
    ordering uses the same descending-score / ascending-index stable
    rule.

    No approximate search.  No Rust path here yet (the Rust binding
    is single-query); Python is canonical.
    """
    M = np.asarray(matrix, dtype=np.float32)
    Q = np.asarray(queries, dtype=np.float32)
    if Q.ndim == 1:
        Q = Q[None, :]
    if M.ndim != 2 or Q.ndim != 2:
        raise ValueError(
            f"vault_recall_batch requires matrix.ndim==2 and queries.ndim in (1, 2); "
            f"got matrix.ndim={M.ndim}, queries.ndim={Q.ndim}"
        )
    if M.shape[1] != Q.shape[1]:
        raise ValueError(
            f"vault_recall_batch shape mismatch: matrix has {M.shape[1]} components "
            f"per row, queries have {Q.shape[1]}"
        )
    N = M.shape[0]
    B = Q.shape[0]
    if N == 0 or top_k <= 0:
        return [[] for _ in range(B)]
    # Component-serial accumulation: scores[b, n] = sum_i metric[i] * M[n,i] * Q[b,i].
    # Folding component-by-component preserves bit-identity with the
    # single-query path (same float32 addition order across i).
    scores = np.zeros((B, N), dtype=np.float32)
    for i in range(M.shape[1]):
        scores += (_CGA_INNER_METRIC[i] * M[:, i])[None, :] * Q[:, i, None]
    k = min(top_k, N)
    out: list[list[tuple[int, float]]] = []
    for b in range(B):
        row = scores[b]
        if k < N:
            cand = np.argpartition(-row, k - 1)[:k]
        else:
            cand = np.arange(N)
        order = np.lexsort((cand, -row[cand]))
        cand = cand[order]
        out.append([(int(i), float(row[i])) for i in cand])
    return out


def unitize_expmap(v: np.ndarray) -> np.ndarray:
    """Unitize a multivector via the Cl(4,1) exponential map.

    Distinguishes boost planes (cosh/sinh) from rotation planes (cos/sin).
    Returns f32 array of length 32.
    """
    if _RUST:
        try:
            return np.asarray(_rs.unitize_expmap(v), dtype=np.float32)
        except (AttributeError, Exception):
            pass
    return None  # caller must fall back to Python implementation


def diffusion_step(
    fields: np.ndarray, edges: np.ndarray, damping: float,
) -> tuple[np.ndarray, float] | None:
    """One forward step of graph diffusion via Rust.

    Returns ``(new_fields, delta)`` or ``None`` if Rust is unavailable
    or not explicitly enabled.

    Pass ``fields`` and ``edges`` as contiguous numpy arrays directly —
    the Rust FFI now consumes them via zero-copy ``PyReadonlyArray2``
    views.  The previous code flattened to Python lists with
    ``.flatten().tolist()``, paying a per-element Python-float
    box-unbox tax on every diffusion step.  ``np.ascontiguousarray``
    is a no-op when the input is already contiguous (the common
    case); the dtype coerce is also a no-op when already float32 /
    int32.
    """
    if _RUST:
        try:
            fields_c = np.ascontiguousarray(fields, dtype=np.float32)
            edges_c = np.ascontiguousarray(edges, dtype=np.int32)
            new_fields, delta = _rs.diffusion_step(
                fields_c, edges_c, float(damping),
            )
            return new_fields, float(delta)
        except (AttributeError, Exception):
            pass
    return None


def using_rust() -> bool:
    """Returns True if the Rust extension is explicitly enabled and loaded."""
    return _RUST
