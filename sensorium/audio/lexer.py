"""
sensorium/audio/lexer.py — acoustic lexer (spec §4).

Operates on measured facts, not semantic guesses. Each frame yields quantized
descriptors so the token stream hashes deterministically (spec §7: quantize
before semantics). Emits AudioTokens in canonical hop order.

Quantization regime (frozen here for v1):
  - log energy   : 1 dB bins (int dB)
  - F0           : 25-cent bins, referenced to 55 Hz (A1)
  - confidences  : uint8 (0..255)
  - spectral     : fixed ordinal centroid bins
All thresholds are module constants so the lexer is a pure function of the
frame matrix.
"""

from __future__ import annotations

import math

import numpy as np

from sensorium.audio.types import AudioToken

EPS = 1e-12

# Quantization / classification constants (v1, frozen).
SILENCE_DB = -55             # frames quieter than this are silence
VOICED_ZCR_MAX = 0.20        # voiced frames have low zero-crossing rate
VOICED_MIN_DB = -45          # and enough energy
F0_REF_HZ = 55.0             # A1 reference for cents
CENTS_BIN = 25               # 25-cent quantization
F0_MIN_HZ = 50.0
F0_MAX_HZ = 500.0
N_CENTROID_BINS = 16
MAX_PITCH_CANDIDATES = 2


def _log_energy_db(frame: np.ndarray) -> float:
    rms = math.sqrt(float(np.mean(frame * frame)) + EPS)
    return 20.0 * math.log10(rms + EPS)


def _zero_crossing_rate(frame: np.ndarray) -> float:
    signs = np.signbit(frame)
    return float(np.count_nonzero(signs[1:] != signs[:-1])) / max(1, frame.size - 1)


def _spectral_centroid_bin(frame: np.ndarray) -> int:
    mag = np.abs(np.fft.rfft(frame * np.hanning(frame.size)))
    total = float(mag.sum()) + EPS
    bins = np.arange(mag.size, dtype=np.float64)
    centroid = float((bins * mag).sum()) / total / max(1, mag.size - 1)  # 0..1
    return int(min(N_CENTROID_BINS - 1, round(centroid * (N_CENTROID_BINS - 1))))


def _hz_to_cents_q(hz: float) -> int:
    cents = 1200.0 * math.log2(max(hz, EPS) / F0_REF_HZ)
    return int(round(cents / CENTS_BIN))


def _pitch_candidates_q(frame: np.ndarray, sample_rate: int) -> tuple[int, ...]:
    """pYIN-style: keep the top autocorrelation peaks (cents_q, prob_q) pairs,
    *before* any Viterbi smoothing (spec §4)."""
    n = frame.size
    ac = np.correlate(frame, frame, mode="full")[n - 1:]
    if ac[0] <= EPS:
        return ()
    ac = ac / ac[0]
    lag_min = max(1, int(sample_rate / F0_MAX_HZ))
    lag_max = min(n - 1, int(sample_rate / F0_MIN_HZ))
    if lag_max <= lag_min:
        return ()
    window = ac[lag_min:lag_max]
    # local maxima
    peaks = [
        lag_min + i
        for i in range(1, window.size - 1)
        if window[i] > window[i - 1] and window[i] >= window[i + 1] and window[i] > 0.3
    ]
    peaks.sort(key=lambda lag: (-float(ac[lag]), lag))
    out: list[int] = []
    for lag in peaks[:MAX_PITCH_CANDIDATES]:
        hz = sample_rate / lag
        prob_q = int(min(255, max(0, round(float(ac[lag]) * 255))))
        out.extend((_hz_to_cents_q(hz), prob_q))
    return tuple(out)


def lex(frames: np.ndarray, sample_rate: int) -> tuple[AudioToken, ...]:
    """Lower a frame matrix into a canonical-ordered tuple of AudioTokens.

    One primary classification token per hop (silence / voiced / unvoiced),
    plus an energy_bin token and, for voiced frames, a pitch_candidates token.
    """
    tokens: list[AudioToken] = []
    for i, frame in enumerate(frames):
        db = _log_energy_db(frame)
        db_q = int(round(db))
        zcr = _zero_crossing_rate(frame)
        tokens.append(AudioToken("energy_bin", i, i + 1, (db_q,)))

        if db_q <= SILENCE_DB:
            tokens.append(AudioToken("silence", i, i + 1, (db_q,)))
            continue

        if zcr <= VOICED_ZCR_MAX and db_q >= VOICED_MIN_DB:
            tokens.append(AudioToken("voiced", i, i + 1, (db_q, int(round(zcr * 255)))))
            cands = _pitch_candidates_q(frame, sample_rate)
            if cands:
                tokens.append(AudioToken("pitch_candidates", i, i + 1, cands))
        else:
            centroid_q = _spectral_centroid_bin(frame)
            tokens.append(AudioToken("unvoiced", i, i + 1, (db_q, centroid_q)))
    return tuple(tokens)
