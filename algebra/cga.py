"""
Conformal Geometric Algebra geometry on Cl(4,1).

Signature: (+,+,+,+,-), with Euclidean coordinates on e1,e2,e3.
The two conformal null directions are built from e4 and e5:

    n_o   = 0.5 * (e4 - e5)   # origin, n_o^2 = 0
    n_inf = e4 + e5           # infinity, n_inf^2 = 0
    n_o · n_inf = -1

A Euclidean point x embeds as:

    X = x + n_o + 0.5 * |x|^2 * n_inf

Then X·X = 0 and X·Y = -0.5 * ||x-y||^2.

This is the ONLY distance metric in CORE-AI.
No cosine similarity. No L2 norm. No approximate indexing.
"""

import numpy as np
from .cl41 import geometric_product, scalar_part, basis_vector, N_COMPONENTS

# Basis-vector component indices for e4/e5 inside the grade-1 block.
# component 1=e1, 2=e2, 3=e3, 4=e4, 5=e5.
_E4_IDX = 4
_E5_IDX = 5

# Pinned magnitude ceiling for f64-exact embedding + read-back (Phase 0A).
# Below this bound, ``embed_point(..., dtype=np.float64)`` round-trips integer
# coordinates exactly through ``read_scalar_e1`` and the conformal distance metric
# stays exact (proven in tests/test_cga_f64_exactness.py). The field-reasoner reader
# REFUSES any quantity whose magnitude exceeds this bound; the refusal lives in the
# reader — this module only states the bound. Generous vs GSM8K (quantities ~< 1e5).
EMBED_EXACT_MAX: int = 1_000_000


def cga_inner(X: np.ndarray, Y: np.ndarray) -> float:
    """
    Symmetric inner product: 0.5 * scalar_part(X*Y + Y*X).
    For null vectors representing conformal points: equals -d^2 / 2.
    """
    XY = geometric_product(X, Y)
    YX = geometric_product(Y, X)
    return 0.5 * scalar_part(XY + YX)


def outer_product(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """
    Outer (wedge) product: X ^ Y.
    For a prompt versor X_p and response versor X_r,
    X_p ^ X_r is a grade-2 object encoding their geometric relationship.
    """
    XY = geometric_product(X, Y)
    YX = geometric_product(Y, X)
    return 0.5 * (XY - YX)


def is_null(X: np.ndarray, tol: float = 1e-6) -> bool:
    """Check if X lies on the null cone: X·X = 0."""
    return abs(cga_inner(X, X)) < tol


def null_project(X: np.ndarray) -> np.ndarray:
    """
    Re-project X onto the null cone by extracting its Euclidean part and
    re-embedding it with the canonical CGA point map.
    """
    euclidean = np.asarray(X, dtype=np.float32)[1:4].copy()
    return embed_point(euclidean)


def embed_point(x: np.ndarray, *, dtype: "np.typing.DTypeLike" = np.float32) -> np.ndarray:
    """
    Embed a Euclidean point x in R^3 into the CGA null cone.

    X = x + n_o + 0.5|x|^2 n_inf,
    where n_o = 0.5(e5-e4), n_inf = e4+e5.

    ``dtype`` defaults to ``float32`` so every existing caller is byte-unchanged.
    The field-reasoner reader passes ``dtype=np.float64`` to get an exact embedding:
    ``geometric_product`` already preserves float64 (``np.result_type``), so the
    only thing that forced f32 was this construction. f32 silently collapses the
    ``n_o`` weight past ~1e4 (the ``0.5|x|^2`` terms lose the ``±1``); f64 keeps it
    exact up to :data:`EMBED_EXACT_MAX` (see tests/test_cga_f64_exactness.py).
    """
    x = np.asarray(x, dtype=dtype)
    assert len(x) == 3, "embed_point expects a 3D vector"

    x_sq = float(np.dot(x, x))
    result = np.zeros(N_COMPONENTS, dtype=dtype)
    result[1:4] = x

    # n_o + 0.5|x|^2 n_inf
    # e4 coefficient: -0.5 + 0.5|x|^2
    # e5 coefficient:  0.5 + 0.5|x|^2
    result[_E4_IDX] = 0.5 * (x_sq - 1.0)
    result[_E5_IDX] = 0.5 * (x_sq + 1.0)
    return result


def read_scalar_e1(X: np.ndarray) -> float:
    """Projective dehomogenization on the e1 axis — the exact, weight-invariant
    read-back of a scalar coordinate from a (possibly dilated) conformal point.

    A point at coordinate ``v`` on the e1 number line embeds as
    ``X = v*e1 + n_o + 0.5 v^2 n_inf``; a uniform conformal dilation by ``k``
    scales the whole null vector. The coordinate is recovered as
    ``e1_coefficient / n_o_weight`` where the n_o weight is ``X[e5] - X[e4]``
    (== 1 for an un-dilated point), so any dilation weight divides out. This is
    the correct read-back for weight-changing operators; a raw distance-from-origin
    is wrong for them.

    Raises ``ValueError`` on a degenerate (zero) n_o weight — a point at infinity
    or an f32 weight-collapse — rather than returning a silently wrong value.
    """
    no_weight = float(X[_E5_IDX] - X[_E4_IDX])
    if no_weight == 0.0:
        raise ValueError(
            "read_scalar_e1: degenerate n_o weight (point at infinity or f32 collapse)"
        )
    return float(X[1]) / no_weight
