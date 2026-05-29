"""
evals/audio_sensorium/synth.py — deterministic fixture synthesis (ADR-0181 PR-4).

Fixtures are described as synthesis specs (``fixtures.json``) rather than
committed .wav blobs: the parameters are diffable and the signal is a pure,
reproducible function of them. The same synthesiser is used by the expected-
artifact generator and by the gate tests, so what is pinned is exactly what is
checked.

`numpy.random.Generator(PCG64)` is bit-reproducible across platforms, and
sine/`standard_normal` results are cast to float32 at the boundary — the cast
absorbs cross-platform ULP noise in the float64 transcendentals, so the
canonical-signal hash is stable across builds (the versor itself is checked
within numeric tolerance — see the eval plan).
"""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 24_000


def _tone(ms: int, hz: float, amp: float, sweep: float) -> np.ndarray:
    n = int(SAMPLE_RATE * ms / 1000)
    t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
    span = t[-1] if t.size > 1 else 1.0
    freq = hz + sweep * (t / span)         # linear F0 sweep over the span
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    return (amp * np.sin(phase)).astype(np.float32)


def _silence(ms: int) -> np.ndarray:
    return np.zeros(int(SAMPLE_RATE * ms / 1000), dtype=np.float32)


def _noise(ms: int, amp: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SAMPLE_RATE * ms / 1000)
    return (amp * rng.standard_normal(n)).astype(np.float32)


def _part(spec: dict) -> np.ndarray:
    kind = spec["kind"]
    if kind == "silence":
        return _silence(int(spec["ms"]))
    if kind == "tone":
        return _tone(int(spec["ms"]), float(spec["hz"]),
                     float(spec.get("amp", 0.5)), float(spec.get("sweep", 0.0)))
    if kind == "noise":
        return _noise(int(spec["ms"]), float(spec.get("amp", 0.3)), int(spec.get("seed", 0)))
    raise ValueError(f"unknown synth kind: {kind!r}")


def synthesize(spec: dict) -> np.ndarray:
    """Return the canonical-rate float32 mono signal for a fixture spec."""
    if spec["kind"] == "concat":
        return np.concatenate([_part(p) for p in spec["parts"]]).astype(np.float32)
    return _part(spec)
