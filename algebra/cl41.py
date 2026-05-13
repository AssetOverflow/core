"""
Cl(4,1) multivector arithmetic.

Signature: (+,+,+,+,-). Basis e1..e5.
Multivectors are float32 arrays of shape (32,) ordered by grade:
  grade-0: index 0        (1 component)
  grade-1: indices 1-5    (5 components)
  grade-2: indices 6-15   (10 components)
  grade-3: indices 16-25  (10 components)
  grade-4: indices 26-30  (5 components)
  grade-5: index 31       (1 component)
"""

from itertools import combinations
from math import comb
import numpy as np

N_DIMS = 5
N_COMPONENTS = 32
SIGNATURE = np.array([1, 1, 1, -1, 1], dtype=np.float64)

# --- Grade offset table ---

def _grade_offsets():
    offsets = []
    start = 0
    for k in range(N_DIMS + 1):
        count = comb(N_DIMS, k)
        offsets.append((start, count))
        start += count
    return offsets

_GRADE_OFFSETS = _grade_offsets()

def grade_start(k: int) -> int:
    return _GRADE_OFFSETS[k][0]

def grade_count(k: int) -> int:
    return _GRADE_OFFSETS[k][1]

# --- Blade index maps ---

def _all_blades():
    """Return ordered list of blade tuples (one per component, ordered by grade)."""
    blades = []
    for k in range(N_DIMS + 1):
        for combo in combinations(range(N_DIMS), k):
            blades.append(combo)
    return blades

_BLADES = _all_blades()  # index -> tuple of basis vector indices
_BLADE_TO_IDX = {b: i for i, b in enumerate(_BLADES)}


def _compute_blade_product(blade_a, blade_b):
    """
    Compute the geometric product of two canonical basis blades.

    For blades A=e_{a1}...e_{am} and B=e_{b1}...e_{bn}, the sign is the
    parity of swaps required to move the concatenated basis list into
    canonical order, multiplied by the metric contractions for repeated
    basis vectors. The resulting blade is the symmetric difference of the
    two blade basis sets.

    This implementation is deliberately bit/set based rather than mutating
    a bubble-sort list while contracting; the previous list mutation path
    corrupted multi-contractions and produced an invalid multiplication
    table.
    """
    sign = 1

    # Anticommutation sign: each pair (a_i, b_j) with a_i > b_j requires
    # one swap to canonicalize A followed by B.
    swaps = 0
    for a in blade_a:
        for b in blade_b:
            if a > b:
                swaps += 1
    if swaps % 2:
        sign *= -1

    # Metric contractions for duplicate basis vectors.
    common = set(blade_a).intersection(blade_b)
    for idx in common:
        sign *= int(SIGNATURE[idx])

    result_blade = tuple(sorted(set(blade_a).symmetric_difference(blade_b)))
    return sign, result_blade


def _build_multiplication_table():
    """Precompute full 32x32 geometric product table."""
    table_idx = np.zeros((N_COMPONENTS, N_COMPONENTS), dtype=np.int32)
    table_sign = np.zeros((N_COMPONENTS, N_COMPONENTS), dtype=np.float32)

    for i, blade_a in enumerate(_BLADES):
        for j, blade_b in enumerate(_BLADES):
            sign, result_blade = _compute_blade_product(blade_a, blade_b)
            table_idx[i, j] = _BLADE_TO_IDX[result_blade]
            table_sign[i, j] = sign

    return table_idx, table_sign

_TABLE_IDX, _TABLE_SIGN = _build_multiplication_table()

# --- Core operations ---

def geometric_product(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Full geometric product in Cl(4,1)."""
    dtype = np.result_type(A, B)
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)
    A = np.asarray(A, dtype=dtype)
    B = np.asarray(B, dtype=dtype)
    result = np.zeros(N_COMPONENTS, dtype=dtype)
    for i in range(N_COMPONENTS):
        ai = A[i]
        if ai == 0.0:
            continue
        for j in range(N_COMPONENTS):
            bj = B[j]
            if bj == 0.0:
                continue
            result[_TABLE_IDX[i, j]] += _TABLE_SIGN[i, j] * ai * bj
    return result

def reverse(A: np.ndarray) -> np.ndarray:
    """
    Reverse (main anti-automorphism).
    Grade-k blades pick up sign (-1)^(k*(k-1)/2).
    Grade 0,1: +1.  Grade 2,3: -1.  Grade 4,5: +1.
    """
    dtype = np.asarray(A).dtype
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)
    A = np.asarray(A, dtype=dtype).copy()
    # Grade 2: indices 6-15
    A[6:16] *= -1.0
    # Grade 3: indices 16-25
    A[16:26] *= -1.0
    return A

def grade_project(A: np.ndarray, k: int) -> np.ndarray:
    """Extract grade-k part of A."""
    dtype = np.asarray(A).dtype
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)
    result = np.zeros(N_COMPONENTS, dtype=dtype)
    start, count = _GRADE_OFFSETS[k]
    result[start:start + count] = A[start:start + count]
    return result

def scalar_part(A: np.ndarray) -> float:
    """Return grade-0 component."""
    return float(A[0])

def norm_squared(A: np.ndarray) -> float:
    """||A||^2 = scalar_part(A * reverse(A))."""
    return scalar_part(geometric_product(A, reverse(A)))

def basis_vector(i: int) -> np.ndarray:
    """Return the i-th basis vector (0-indexed) as a 32-component multivector."""
    v = np.zeros(N_COMPONENTS, dtype=np.float32)
    v[1 + i] = 1.0
    return v
