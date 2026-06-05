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
from .cl41 import (
    geometric_product,
    grade_project,
    reverse,
    scalar_part,
    N_COMPONENTS,
)

# The unit pseudoscalar I5 = e1 e2 e3 e4 e5 (the grade-5 blade, component 31).
# In Cl(4,1) with signature (+,+,+,+,-), I5^2 = -1, so I5^{-1} = -I5. Used by
# ``dual`` / ``meet``. Module-level singleton; never mutated.
_PSEUDOSCALAR_INDEX = 31
_I5 = np.zeros(N_COMPONENTS, dtype=np.float64)
_I5[_PSEUDOSCALAR_INDEX] = 1.0

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
    """The antisymmetric (commutator) product ``0.5 * (XY - YX)``.

    HONEST CONTRACT: this equals the grade-raising wedge ``X ^ Y`` **only when both
    operands are grade 1** (vectors). For higher-grade operands it is the *commutator*
    (Lie bracket), which is NOT the wedge — in particular it does NOT build a k-blade
    by repeated application (a bivector commuted with a vector collapses the grade-3
    part to grade 1). Existing callers use the result as an opaque, deterministic
    relationship feature (folded into a scalar via :func:`cga_inner`), where the
    commutator is well-defined regardless; none read it by grade.

    For the true grade-raising exterior product (lines/planes/incidence) use
    :func:`graded_wedge`. (Renamed contract only — behaviour is unchanged, so every
    current caller is byte-identical.)
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


# ---------------------------------------------------------------------------
# Incidence algebra — the corrected grade-raising wedge, dual, and meet.
# These let the inner product operate on RELATIONS among entities (lines, planes,
# incidence) rather than only pairwise point distance. Built only from the existing
# Cl(4,1) primitives (geometric_product, grade_project) + the pseudoscalar; they add
# no normalization, no approximation, and leave the versor_condition path untouched
# (flats are null-cone outer products, not unit versors).
# ---------------------------------------------------------------------------

_MAX_GRADE = 5  # Cl(4,1): grades 0..5


def blade_grade(X: np.ndarray) -> int:
    """The single grade of a homogeneous blade. Raises if X is zero or grade-mixed.

    Grade is detected by EXACT nonzero (no tolerance): integer-coordinate embeddings
    produce exact integer blades in float64, so a grade block is exactly 0 or not.
    """
    grades = [k for k in range(_MAX_GRADE + 1) if np.any(grade_project(X, k))]
    if len(grades) != 1:
        raise ValueError(f"not a homogeneous blade: nonzero grades {grades}")
    return grades[0]


def graded_wedge(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """The true grade-raising exterior product ``X ^ Y`` for homogeneous blades.

    ``X ^ Y = <X Y>_{grade(X)+grade(Y)}`` — the top-grade part of the geometric
    product. Unlike :func:`outer_product` (the commutator) this composes correctly:
    ``graded_wedge(graded_wedge(P, Q), n_inf)`` builds the grade-3 line P^Q^n_inf,
    and so on. If the grades sum past the pseudoscalar (>5) the wedge is identically
    zero. For two grade-1 vectors it agrees with :func:`outer_product` exactly.
    """
    gx, gy = blade_grade(X), blade_grade(Y)
    if gx + gy > _MAX_GRADE:
        return np.zeros(N_COMPONENTS, dtype=geometric_product(X, Y).dtype)
    return grade_project(geometric_product(X, Y), gx + gy)


def blade_norm(X: np.ndarray) -> float:
    """Reversion norm ``sqrt(|<X reverse(X)>_0|)`` — zero iff X is the zero blade."""
    return float(np.sqrt(abs(scalar_part(geometric_product(X, reverse(X))))))


def is_incident(point: np.ndarray, flat: np.ndarray) -> bool:
    """Exact incidence test: is ``point`` on ``flat`` (a line/plane OPNS blade)?

    True iff ``point ^ flat == 0`` EXACTLY (every component zero) — no float
    tolerance to admit (the wrong=0 discipline: a near-incident point is REFUSED,
    not admitted). Exact for integer-coordinate points within ``EMBED_EXACT_MAX``.
    """
    return not bool(np.any(graded_wedge(point, flat)))


def dual(X: np.ndarray) -> np.ndarray:
    """Pseudoscalar dual ``X * I5^{-1}`` (``I5^{-1} = -I5`` since ``I5^2 = -1``).

    Maps a grade-k blade to grade ``5-k``. Involutive up to sign:
    ``dual(dual(X)) == -X``.
    """
    return geometric_product(X, -_I5)


def meet(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """The meet (intersection) ``dual(dual(A) ^ dual(B))`` of two homogeneous blades.

    Correct for operands in GENERAL POSITION whose join spans the space — e.g. two
    non-parallel planes meet in their intersection line. The grade of the result is
    ``grade(A)+grade(B)-5``.

    HONEST ENVELOPE: this full-pseudoscalar meet DEGENERATES for operands that share
    a proper subspace (e.g. two coplanar lines, two parallel planes): the inner wedge
    ``dual(A) ^ dual(B)`` is then identically zero, so ``meet`` returns the **zero
    multivector** — a detectable signal of "no transversal meet", never a silently
    wrong value. The general intersection of such operands (e.g. the point where two
    coplanar lines cross) requires the *join-relative* meet, which is deliberately
    NOT implemented here; the caller MUST check ``blade_norm(result) == 0`` and treat
    zero as degenerate/refuse rather than as a geometric object.
    """
    return dual(graded_wedge(dual(A), dual(B)))
