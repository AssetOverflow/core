"""
Backend dispatch: use Rust extension (core_rs) when available,
fall back to pure Python (algebra/cl41.py etc.) transparently.

This module is the single switch. All algebra modules import from here
for performance-critical ops. Pure Python is always the fallback —
the system is never broken by a missing Rust build.

Usage:
    from algebra.backend import geometric_product, versor_apply, cga_inner, vault_recall
"""

import numpy as np

try:
    import core_rs as _rs
    _RUST = True
except ImportError:
    _RUST = False


def geometric_product(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    if _RUST:
        return np.asarray(_rs.geometric_product(A, B), dtype=np.float32)
    from algebra.cl41 import geometric_product as _gp
    return _gp(A, B)


def versor_apply(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    if _RUST and np.result_type(V, F) != np.dtype(np.float64):
        return np.asarray(_rs.versor_apply(V, F), dtype=np.float32)
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


def vault_recall(versors: list, query: np.ndarray, top_k: int = 5) -> list:
    """
    Top-k CGA inner product recall.
    Rust path: parallel Rayon scan (releases GIL, true multithreaded).
    Python path: sequential list comprehension.
    """
    if _RUST:
        try:
            results = _rs.vault_recall(versors, query, top_k)
            return results
        except Exception:
            pass
    q = np.asarray(query)
    scores = [(i, float(cga_inner(q, np.asarray(v)))) for i, v in enumerate(versors)]
    scores.sort(key=lambda x: -x[1])
    return scores[:top_k]


def using_rust() -> bool:
    """Returns True if the Rust extension is loaded."""
    return _RUST
