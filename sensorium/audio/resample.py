"""
sensorium/audio/resample.py — deterministic polyphase FIR resampling (spec §3).

SciPy is intentionally NOT a dependency (it is absent from the runtime and
CLAUDE.md forbids broad infrastructure). This is a pure-numpy polyphase FIR
upsample→filter→downsample, equivalent in form to scipy.signal.resample_poly
with explicit FIR coefficients. The FIR taps are a pack artifact in PR-3
(`resample_fir_v1.npy`); this module only *applies* them, deterministically.

Replayability requirements (spec §3 / §7):
  - odd-length symmetric FIR → zero-phase (group delay = (len-1)/2 samples).
  - float64 internal compute; the caller casts to float32 at the boundary.
  - same-rate input is an exact passthrough (no filtering, no drift).
"""

from __future__ import annotations

from math import gcd

import numpy as np


def resample_poly(x: np.ndarray, up: int, down: int, fir: np.ndarray) -> np.ndarray:
    """Resample ``x`` by the rational factor ``up/down`` using explicit FIR taps.

    The FIR must be a low-pass designed for the ``up`` insertion rate. An
    odd-length symmetric FIR yields zero-phase output (the group delay is
    removed by centering). Deterministic for fixed (x, up, down, fir).
    """
    if up < 1 or down < 1:
        raise ValueError(f"up/down must be >= 1, got up={up}, down={down}")
    if fir.ndim != 1 or fir.size % 2 == 0:
        raise ValueError("FIR must be a 1-D odd-length (symmetric) array")

    g = gcd(up, down)
    up, down = up // g, down // g
    xf = np.asarray(x, dtype=np.float64)

    # Upsample by zero-insertion.
    upsampled = np.zeros(xf.size * up, dtype=np.float64)
    upsampled[::up] = xf

    # Zero-phase FIR via centered 'same' convolution, scaled by up to
    # preserve amplitude through zero-insertion.
    taps = np.asarray(fir, dtype=np.float64) * up
    filtered = np.convolve(upsampled, taps, mode="same")

    # Downsample by decimation.
    return filtered[::down]


def needs_resample(sample_rate: int, target_sr: int) -> bool:
    return sample_rate != target_sr
