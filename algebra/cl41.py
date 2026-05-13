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
SIGNATURE = np.array([1, 1, 1, 1, -1], dtype=np.float64)

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

def _blade_product(blade_a, blade_b):
    """Compute geometric product of two basis blades. Returns (sign, result_blade_tuple)."""
    # Concatenate and bubble-sort, tracking sign flips and metric contractions
    seq = list(blade_a) + list(blade_b)
    sign = 1
    # Bubble sort to canonical order, tracking swaps
    n = len(seq)
    for i in range(n):
        for j in range(n - i - 1):
            if seq[j] > seq[j + 1]:
                seq[j], seq[j + 1] = seq[j + 1], seq[j]
                sign *= -1
            elif seq[j] == seq[j + 1]:
                # Metric contraction: e_i^2 = signature[i]
                metric = int(SIGNATURE[seq[j]])
                sign *= metric
                seq.pop(j)
                seq.pop(j)  # second element now at same index after first pop
                n -= 2
                break
        else:
            continue
        break
    # After contraction there may still be duplicates — recurse
    result = tuple(sorted(set(seq)))  # this is wrong for multi-contraction; use proper loop
    return sign, tuple(seq)

def _build_multiplication_table():
    """Precompute full 32x32 geometric product table."""
    table_idx = np.zeros((N_COMPONENTS, N_COMPONENTS), dtype=np.int32)
    table_sign = np.zeros((N_COMPONENTS, N_COMPONENTS), dtype=np.float32)

    for i, blade_a in enumerate(_BLADES):
        for j, blade_b in enumerate(_BLADES):
            sign, result_blade = _compute_blade_product(blade_a, blade_b)
            result_idx = _BLADE_TO_IDX.get(result_blade, 0)
            table_idx[i, j] = result_idx
            table_sign[i, j] = sign

    return table_idx, table_sign

def _compute_blade_product(blade_a, blade_b):
    """Compute geometric product of two basis blades via bubble sort + metric."""
    seq = list(blade_a) + list(blade_b)
    sign = 1
    i = 0
    while i < len(seq) - 1:
        j = i
        while j < len(seq) - 1:
            if seq[j] == seq[j + 1]:
                # Contract: e_k^2 = signature[k]
                sign *= int(SIGNATURE[seq[j]])
                seq.pop(j)
                seq.pop(j)
                if j > 0:
                    i = max(0, j - 1)
                break
            elif seq[j] > seq[j + 1]:
                seq[j], seq[j + 1] = seq[j + 1], seq[j]
                sign *= -1
                j += 1
            else:
                j += 1
        else:
            i += 1
    result_blade = tuple(seq)
    if result_blade not in _BLADE_TO_IDX:
        return 0, ()
    return sign, result_blade

_TABLE_IDX, _TABLE_SIGN = _build_multiplication_table()

# --- Core operations ---

def geometric_product(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Full geometric product in Cl(4,1)."""
    A = np.asarray(A, dtype=np.float32)
    B = np.asarray(B, dtype=np.float32)
    result = np.zeros(N_COMPONENTS, dtype=np.float32)
    for i in range(N_COMPONENTS):
        if A[i] == 0.0:
            continue
        for j in range(N_COMPONENTS):
            if B[j] == 0.0:
                continue
            result[_TABLE_IDX[i, j]] += _TABLE_SIGN[i, j] * A[i] * B[j]
    return result

def reverse(A: np.ndarray) -> np.ndarray:
    """
    Reverse (main anti-automorphism).
    Grade-k blades pick up sign (-1)^(k*(k-1)/2).
    Grade 0,1: +1.  Grade 2,3: -1.  Grade 4,5: +1.
    """
    A = np.asarray(A, dtype=np.float32).copy()
    # Grade 2: indices 6-15
    A[6:16] *= -1.0
    # Grade 3: indices 16-25
    A[16:26] *= -1.0
    return A

def grade_project(A: np.ndarray, k: int) -> np.ndarray:
    """Extract grade-k part of A."""
    result = np.zeros(N_COMPONENTS, dtype=np.float32)
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
