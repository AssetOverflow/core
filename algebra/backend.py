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


def geometric_product(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    if _RUST:
        return np.asarray(_rs.geometric_product(A, B), dtype=np.float32)
    from algebra.cl41 import geometric_product as _gp
    return _gp(A, B)


def versor_apply(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Apply a versor through the canonical algebra closure boundary.

    The Python implementation is the default source of truth for runtime
    closure semantics.  The Rust closure path is used only when explicitly
    requested with CORE_BACKEND=rust/core_rs.
    """
    if _RUST:
        try:
            return np.asarray(_rs.versor_apply_with_closure(V, F), dtype=np.float64)
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


def vault_recall(versors: list, query: np.ndarray, top_k: int = 5) -> list:
    """
    Top-k CGA inner product recall.
    Rust path: parallel Rayon scan when explicitly enabled.
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

    Returns (new_fields, delta) or None if Rust is unavailable or not explicitly enabled.
    """
    if _RUST:
        try:
            n_nodes = fields.shape[0]
            fields_flat = fields.astype(np.float32).flatten().tolist()
            edges_flat = edges.astype(np.int32).flatten().tolist()
            new_fields, delta = _rs.diffusion_step(
                fields_flat, edges_flat, n_nodes, float(damping),
            )
            return np.asarray(new_fields, dtype=np.float32), float(delta)
        except (AttributeError, Exception):
            pass
    return None


def using_rust() -> bool:
    """Returns True if the Rust extension is explicitly enabled and loaded."""
    return _RUST
