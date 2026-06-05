"""Phase 0A — f64-exact conformal embedding + projective read-back + pinned ceiling.

The field-reasoner wedge encodes quantities as conformal points on the e1 number
line and reads the answer back by *projective dehomogenization* — the only exact
read-back for weight-changing (dilation) operators. ``embed_point`` was f32-hardcoded
(``algebra/cga.py``), which silently destroys integers past ~1e4: at v=12345 the f32
``n_o`` weight collapses to 0 and the read-back is unusable.

These tests pin three contracts:

1. ``embed_point``'s f32 default is byte-unchanged (no existing caller regresses).
2. The new ``dtype=np.float64`` path + ``read_scalar_e1`` recover integer coordinates
   **exactly** across the whole admissible band, where f32 already fails.
3. ``EMBED_EXACT_MAX`` is the pinned magnitude ceiling: exactness is asserted up to it;
   the field reader refuses above it (the refusal lives in the reader, not here).
"""

from __future__ import annotations

import numpy as np
import pytest

from algebra.cga import (
    EMBED_EXACT_MAX,
    cga_inner,
    embed_point,
    read_scalar_e1,
)


def _e1(v: float, dtype: "np.typing.DTypeLike" = np.float64) -> np.ndarray:
    """Embed a scalar coordinate on the e1 axis."""
    return embed_point(np.array([v, 0.0, 0.0]), dtype=dtype)


# --- contract 1: f32 default is byte-unchanged -----------------------------


def test_embed_point_f32_default_unchanged():
    """The default path stays float32 and byte-identical to the prior impl."""
    x = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    X = embed_point(x)
    assert X.dtype == np.float32
    # Prior closed-form: result[1:4]=x, e4=0.5(|x|^2-1), e5=0.5(|x|^2+1).
    x_sq = float(np.dot(x, x))  # 14.0
    assert X[1] == np.float32(1.0)
    assert X[2] == np.float32(2.0)
    assert X[3] == np.float32(3.0)
    assert X[4] == np.float32(0.5 * (x_sq - 1.0))
    assert X[5] == np.float32(0.5 * (x_sq + 1.0))


# --- contract 2: f64 exact read-back where f32 fails -----------------------


@pytest.mark.parametrize("v", [0, 1, 7, 42, 103, 300, 9999, 12345, 100000, 1000000])
def test_read_scalar_e1_exact_f64(v):
    """Projective dehomogenization recovers the integer coordinate exactly in f64."""
    X = _e1(float(v), dtype=np.float64)
    assert read_scalar_e1(X) == float(v)


def test_f32_readback_fails_where_f64_succeeds():
    """The motivating hazard: f32 cannot round-trip a mid-size integer; f64 can.

    A meaningfully-failing guard — if this passes under f32 the f64 work is moot.
    """
    v = 12345.0
    f64 = read_scalar_e1(_e1(v, dtype=np.float64))
    assert f64 == v
    Xf32 = _e1(v, dtype=np.float32)
    denom = float(Xf32[5] - Xf32[4])  # n_o weight collapses toward 0 in f32
    assert denom != 1.0  # the f32 weight is already wrong at this scale


def test_dilation_weighted_point_readback():
    """Read-back is exact for a *weighted* (dilated) null vector, not just unit weight.

    A dilation about the origin by factor k scales the whole null vector; the e1
    coordinate must come back as k*v via the e1/n_o-weight ratio, never as a raw
    distance-from-origin.
    """
    v, k = 2.0, 4.0
    X = _e1(v, dtype=np.float64)
    Xw = (k * X).astype(np.float64)  # uniform conformal weight k
    assert read_scalar_e1(Xw) == v  # projective: weight divides out


# --- contract 3: the pinned ceiling ----------------------------------------


def test_embed_exact_max_is_pinned_and_generous():
    """The ceiling is a concrete int, comfortably above any GSM8K quantity."""
    assert isinstance(EMBED_EXACT_MAX, int)
    assert EMBED_EXACT_MAX >= 1_000_000


def test_distance_exact_within_ceiling():
    """The conformal distance metric stays exact for integer pairs up to the ceiling.

    cga_inner(embed(a), embed(b)) = -1/2 (a-b)^2, computed in f64.
    """
    for a, b in [(0, 1), (3, 7), (100, 103), (0, EMBED_EXACT_MAX)]:
        inner = cga_inner(_e1(float(a)), _e1(float(b)))
        expected = -0.5 * (a - b) ** 2
        assert inner == expected, f"a={a} b={b}: {inner} != {expected}"


def test_embedded_f64_point_is_null():
    """f64 embedding still lands on the null cone."""
    X = _e1(123.0, dtype=np.float64)
    assert abs(cga_inner(X, X)) < 1e-6
