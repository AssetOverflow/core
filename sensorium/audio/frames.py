"""
sensorium/audio/frames.py — fixed frame grid (spec §4).

Default 20 ms window / 10 ms hop. Deterministic: the last partial frame is
zero-padded to the full window length so the grid is a pure function of
(signal length, sample_rate, frame_ms, hop_ms).
"""

from __future__ import annotations

import numpy as np

FRAME_MS = 20
HOP_MS = 10


def frame_signal(
    samples: np.ndarray,
    sample_rate: int,
    *,
    frame_ms: int = FRAME_MS,
    hop_ms: int = HOP_MS,
) -> np.ndarray:
    """Return a (n_frames, frame_len) float64 matrix of zero-padded frames.

    The number of frames is ``ceil((n - frame_len)/hop) + 1`` for n >=
    frame_len, else 1 (a single zero-padded frame). Hop index i spans samples
    [i*hop, i*hop+frame_len).
    """
    x = np.asarray(samples, dtype=np.float64)
    frame_len = max(1, int(round(sample_rate * frame_ms / 1000)))
    hop_len = max(1, int(round(sample_rate * hop_ms / 1000)))

    if x.size <= frame_len:
        n_frames = 1
    else:
        n_frames = (x.size - frame_len) // hop_len + 1
        # Cover the tail with one more zero-padded frame when it spills over.
        if (n_frames - 1) * hop_len + frame_len < x.size:
            n_frames += 1

    out = np.zeros((n_frames, frame_len), dtype=np.float64)
    for i in range(n_frames):
        start = i * hop_len
        chunk = x[start:start + frame_len]
        out[i, : chunk.size] = chunk
    return out
