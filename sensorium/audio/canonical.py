"""
sensorium/audio/canonical.py — canonical signal formation (spec §3).

Default: mono, 24 kHz, float32 internal-as-float64 compute. The original
source bytes are hashed for provenance (``source_sha256``); the canonical
float32 image is hashed as ``canonical_sha256``. Resampling, when needed, uses
the pinned polyphase FIR from the pack (PR-3); PR-2 supports the same-rate
passthrough path and resampling when explicit FIR taps are supplied.
"""

from __future__ import annotations

import numpy as np

from sensorium.audio.checksum import sha256_array
from sensorium.audio.resample import needs_resample, resample_poly
from sensorium.audio.types import AudioSignal

CANONICAL_SAMPLE_RATE = 24_000


def to_mono(samples: np.ndarray) -> np.ndarray:
    """Deterministic mono downmix: average across channels if multi-channel.

    Accepts (N,) mono, (N, C) or (C, N) interleaved/planar. Channel axis is
    the smaller of the two dimensions (audio has more samples than channels).
    """
    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim == 1:
        return arr
    if arr.ndim != 2:
        raise ValueError(f"expected 1-D or 2-D samples, got ndim={arr.ndim}")
    channel_axis = 0 if arr.shape[0] < arr.shape[1] else 1
    return arr.mean(axis=channel_axis)


def canonicalize(
    samples: np.ndarray,
    sample_rate: int,
    *,
    target_sr: int = CANONICAL_SAMPLE_RATE,
    fir: np.ndarray | None = None,
    start_ms: int = 0,
) -> AudioSignal:
    """Produce a canonical mono float32 ``AudioSignal`` with provenance hashes.

    ``source_sha256`` hashes the original input bytes exactly as received;
    ``canonical_sha256`` hashes the canonical float32 image. Resampling to
    ``target_sr`` requires explicit ``fir`` taps (the pinned pack artifact);
    same-rate input is an exact passthrough.
    """
    source_sha256 = sha256_array(np.asarray(samples, dtype=np.float32))
    mono = to_mono(samples)

    if needs_resample(sample_rate, target_sr):
        if fir is None:
            raise ValueError(
                f"resampling {sample_rate}->{target_sr} requires explicit FIR taps "
                "(pinned pack artifact, PR-3); none supplied"
            )
        from math import gcd
        g = gcd(target_sr, sample_rate)
        mono = resample_poly(mono, up=target_sr // g, down=sample_rate // g, fir=fir)

    canonical = np.ascontiguousarray(mono, dtype=np.float32)
    duration_ms = int(round(1000 * canonical.size / target_sr))
    return AudioSignal(
        samples=canonical,
        sample_rate=target_sr,
        start_ms=start_ms,
        end_ms=start_ms + duration_ms,
        source_sha256=source_sha256,
        canonical_sha256=sha256_array(canonical),
    )
