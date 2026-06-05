"""CGA incidence algebra — the corrected grade-raising wedge, dual, and meet.

These primitives let `cga_inner` operate on RELATIONS among entities (lines, planes,
incidence) rather than only pairwise point distance — the missing "wire" for the
section-level relational layer. Every test pins EXACT behaviour (integer-coordinate
embeddings → exact integer blades in float64), no float tolerance to admit.

It also pins the honest distinction the `outer_product` docstring now states: the
corrected `graded_wedge` agrees with `outer_product` for grade-1 vectors but DIFFERS
for higher grades (where `outer_product` is the commutator, not the wedge) — and the
honest envelope of `meet` (degenerate operands return zero, never a silent wrong).
"""

from __future__ import annotations

import numpy as np

from algebra.cga import (
    EMBED_EXACT_MAX,
    blade_grade,
    blade_norm,
    dual,
    embed_point,
    graded_wedge,
    is_incident,
    meet,
    outer_product,
)
from algebra.cl41 import N_COMPONENTS, geometric_product, scalar_part

_F64 = np.float64


def _pt(x: float, y: float = 0.0, z: float = 0.0) -> np.ndarray:
    return embed_point(np.array([x, y, z], dtype=_F64), dtype=_F64)


def _n_inf() -> np.ndarray:
    v = np.zeros(N_COMPONENTS, dtype=_F64)
    v[4] = 1.0
    v[5] = 1.0
    return v


def _line(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """OPNS line p ^ q ^ n_inf (grade 3)."""
    return graded_wedge(graded_wedge(p, q), _n_inf())


def _plane(p: np.ndarray, q: np.ndarray, r: np.ndarray) -> np.ndarray:
    """OPNS plane p ^ q ^ r ^ n_inf (grade 4)."""
    return graded_wedge(graded_wedge(graded_wedge(p, q), r), _n_inf())


# --- graded_wedge agrees with outer_product on grade-1, differs above ------


def test_graded_wedge_agrees_with_outer_product_for_vectors():
    a = np.zeros(N_COMPONENTS, dtype=_F64); a[1] = 1.0   # e1
    b = np.zeros(N_COMPONENTS, dtype=_F64); b[2] = 1.0   # e2
    np.testing.assert_array_equal(graded_wedge(a, b), outer_product(a, b))
    assert blade_grade(graded_wedge(a, b)) == 2


def test_graded_wedge_differs_from_commutator_above_grade_1():
    """The honest distinction outer_product's docstring now states: building a
    3-blade by repeated wedge works for graded_wedge but COLLAPSES for the commutator."""
    p, q, ninf = _pt(0, 0), _pt(2, 0), _n_inf()
    pq = graded_wedge(p, q)              # grade 2
    line_true = graded_wedge(pq, ninf)   # grade 3 — the real line
    line_commutator = outer_product(pq, ninf)
    assert blade_grade(line_true) == 3
    # the commutator does NOT yield the grade-3 line (it collapses the top grade)
    assert not np.array_equal(line_true, line_commutator)


# --- incidence: exact, and exact at scale (f64) ----------------------------


def test_incidence_collinear_exact():
    line = _line(_pt(0, 0), _pt(2, 0))
    assert is_incident(_pt(5, 0), line)     # collinear beyond the segment
    assert is_incident(_pt(1, 0), line)     # on the segment
    assert not is_incident(_pt(0, 1), line)  # off the line
    assert not is_incident(_pt(3, 2), line)


def test_incidence_exact_at_scale():
    """f64 keeps incidence exact for large integer coordinates (within the ceiling)."""
    v = EMBED_EXACT_MAX // 2
    line = _line(_pt(0, 0), _pt(2, 0))      # the x-axis
    assert is_incident(_pt(float(v), 0), line)
    assert not is_incident(_pt(float(v), 1), line)


# --- dual ------------------------------------------------------------------


def test_pseudoscalar_squares_to_minus_one():
    i5 = np.zeros(N_COMPONENTS, dtype=_F64); i5[31] = 1.0
    assert scalar_part(geometric_product(i5, i5)) == -1.0


def test_dual_is_involution_up_to_sign():
    x = _pt(3, 0)
    np.testing.assert_allclose(dual(dual(x)), -x, atol=0.0)


# --- meet: correct for spanning operands, honest-zero for degenerate -------


def test_meet_of_two_planes_is_their_line():
    p_z0 = _plane(_pt(0, 0, 0), _pt(1, 0, 0), _pt(0, 1, 0))   # z = 0
    p_y0 = _plane(_pt(0, 0, 0), _pt(1, 0, 0), _pt(0, 0, 1))   # y = 0
    line = meet(p_z0, p_y0)                                    # expect the x-axis
    assert blade_norm(line) != 0.0
    assert blade_grade(line) == 3
    assert is_incident(_pt(5, 0, 0), line)     # x-axis point is on it
    assert not is_incident(_pt(0, 5, 0), line)  # off it


def test_meet_degenerate_operands_return_zero_not_silent_wrong():
    """The honest envelope: coplanar lines do not span, so the full-pseudoscalar meet
    DEGENERATES — it returns the zero multivector (detectable), never a wrong object."""
    l1 = _line(_pt(0, 0), _pt(2, 0))    # x-axis (z=0 plane)
    l2 = _line(_pt(1, -1), _pt(1, 1))   # x=1 vertical (z=0 plane) — coplanar with l1
    result = meet(l1, l2)
    assert blade_norm(result) == 0.0   # degenerate → zero, caller must refuse
