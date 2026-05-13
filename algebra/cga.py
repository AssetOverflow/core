"""
Conformal Geometric Algebra geometry on Cl(4,1).

Key identity: for null vectors X, Y on the horosphere,
    cga_inner(X, Y) = -d(X, Y)^2 / 2
where d is Euclidean distance.

This is the ONLY distance metric in CORE-AI.
No cosine similarity. No L2 norm. No approximate indexing.
"""

import numpy as np
from .cl41 import geometric_product, reverse, scalar_part, basis_vector, N_COMPONENTS


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
    A real (non-imaginary) result means the dialogue is coherent.
    """
    XY = geometric_product(X, Y)
    YX = geometric_product(Y, X)
    return 0.5 * (XY - YX)


def is_null(X: np.ndarray, tol: float = 1e-6) -> bool:
    """Check if X lies on the null cone: X*X = 0."""
    return abs(cga_inner(X, X)) < tol


def null_project(X: np.ndarray) -> np.ndarray:
    """
    Re-project X onto the null cone.
    Call on vault entries periodically to correct floating-point null-cone drift.
    This is numerical maintenance, not a heat shield.
    Method: extract Euclidean part, re-embed via standard CGA point map.
    """
    euclidean = X[1:4].copy().astype(np.float32)
    x_sq = float(np.dot(euclidean, euclidean))
    result = np.zeros(N_COMPONENTS, dtype=np.float32)
    result[1:4] = euclidean
    result[4] = 0.5 * x_sq   # e+ coefficient
    result[5] = 1.0           # e- coefficient
    return result


def embed_point(x: np.ndarray) -> np.ndarray:
    """
    Embed a Euclidean point x in R^3 into the CGA null cone.
    Standard map: X = x + (1/2)|x|^2 * e+ + e-
    """
    x = np.asarray(x, dtype=np.float32)
    assert len(x) == 3, "embed_point expects a 3D vector"
    result = np.zeros(N_COMPONENTS, dtype=np.float32)
    result[1:4] = x
    result[4] = 0.5 * float(np.dot(x, x))
    result[5] = 1.0
    return result
