"""
Conformal Geometric Algebra geometry on Cl(4,1).

Signature: (+,+,+,+,-), with Euclidean coordinates on e1,e2,e3.
The two conformal null directions are built from e4 and e5:

    n_o   = 0.5 * (e5 - e4)   # origin, n_o^2 = 0
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


def embed_point(x: np.ndarray) -> np.ndarray:
    """
    Embed a Euclidean point x in R^3 into the CGA null cone.

    X = x + n_o + 0.5|x|^2 n_inf,
    where n_o = 0.5(e5-e4), n_inf = e4+e5.
    """
    x = np.asarray(x, dtype=np.float32)
    assert len(x) == 3, "embed_point expects a 3D vector"

    x_sq = float(np.dot(x, x))
    result = np.zeros(N_COMPONENTS, dtype=np.float32)
    result[1:4] = x

    # n_o + 0.5|x|^2 n_inf
    # e4 coefficient: -0.5 + 0.5|x|^2
    # e5 coefficient:  0.5 + 0.5|x|^2
    result[_E4_IDX] = 0.5 * (x_sq - 1.0)
    result[_E5_IDX] = 0.5 * (x_sq + 1.0)
    return result
