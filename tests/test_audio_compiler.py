"""
ADR-0181 PR-2 — deterministic audio substrate tests.

Covers the substrate's load-bearing invariants (the audio analogs of
ADR-0180 §1.5.4 T-1..T-4 named A-1..A-6 in ADR-0181 §4.2):

  A-1  determinism: same canonical bytes + same pack ⇒ byte-identical (32,)
  A-4  serialization barrier: in-chunk compile_events is order-sensitive
  A-5  versor condition: every emitted unit < 1e-6 (never weakened)
  A-6  trace hygiene: no PCM in the evidence trace
  + projection shape/dtype, IR-replay, elliptic-only operator guard.

Fixtures are deterministic synthetic signals (silence, voiced tone with a
rising contour, broadband noise) at the canonical 24 kHz, so no resampling
FIR (a PR-3 pack artifact) is needed.
"""

from __future__ import annotations

import numpy as np
import pytest

from sensorium.audio import (
    AudioCompiler,
    AudioCompilationUnit,
    audio_evidence_trace,
    build_elliptic_rotor,
)
from sensorium.audio.compiler import compile_events
from sensorium.audio.operators import (
    DEFAULT_OPERATOR_REGISTRY,
    ELLIPTIC_PLANES,
    OperatorSpec,
)
from sensorium.audio.types import AuditoryEvent
from algebra.versor import versor_condition

SR = 24_000


# --------------------------------------------------------------------------
# Synthetic fixtures
# --------------------------------------------------------------------------

def _silence(ms: int = 500) -> np.ndarray:
    return np.zeros(int(SR * ms / 1000), dtype=np.float32)


def _tone(hz: float, ms: int, amp: float = 0.5, sweep: float = 0.0) -> np.ndarray:
    n = int(SR * ms / 1000)
    t = np.arange(n, dtype=np.float64) / SR
    freq = hz + sweep * t / max(t[-1], 1e-9)   # linear sweep over the span
    phase = 2 * np.pi * np.cumsum(freq) / SR
    return (amp * np.sin(phase)).astype(np.float32)


def _noise(ms: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * ms / 1000)
    return (0.3 * rng.standard_normal(n)).astype(np.float32)


def _compile(samples: np.ndarray) -> AudioCompilationUnit:
    return AudioCompiler().compile(samples, SR)


# --------------------------------------------------------------------------
# Shape / dtype / versor condition
# --------------------------------------------------------------------------

@pytest.mark.parametrize("signal", [
    _silence(300),
    _tone(160.0, 400, sweep=80.0),
    _noise(300),
    np.concatenate([_tone(150.0, 300), _silence(400), _tone(150.0, 300, sweep=60.0)]),
])
def test_projection_shape_dtype_and_versor_condition(signal):
    unit = _compile(signal)
    assert unit.versor.shape == (32,)            # projection shape
    assert unit.versor.dtype == np.float32       # projection dtype
    assert unit.versor_condition < 1e-6          # A-5, never weakened


# --------------------------------------------------------------------------
# A-1 — determinism
# --------------------------------------------------------------------------

def test_a1_compile_is_byte_identical_across_calls():
    sig = np.concatenate([_tone(160.0, 350, sweep=90.0), _silence(350), _noise(200, 7)])
    u1 = _compile(sig)
    u2 = _compile(sig)
    assert np.array_equal(u1.versor, u2.versor)
    assert u1.merge_key == u2.merge_key
    assert u1.ir_sha256 == u2.ir_sha256
    assert u1.projection_sha256 == u2.projection_sha256


def test_a1_same_bytes_same_merge_key_idempotent():
    """The strict invariant tail (ADR-0181 §4.3): same canonical bytes ⇒ same
    merge key ⇒ CRDT-idempotent."""
    sig = _tone(200.0, 300)
    assert _compile(sig).merge_key == _compile(sig.copy()).merge_key


# --------------------------------------------------------------------------
# A-4 — serialization barrier (compile_events is order-sensitive)
# --------------------------------------------------------------------------

def test_a4_compile_events_is_order_sensitive():
    """Swapping two events in the fold changes the versor — proving the barrier
    is real (non-commutative composition). If this passes trivially (orders
    equal), the substrate could be wrongly sharded (ADR-0181 §2.1)."""
    e_speech = AuditoryEvent("speech.voiced", 0, 5, (("dur_hops", 5),), ())
    e_pause = AuditoryEvent("pause.short", 5, 9, (("dur_hops", 4),), ())
    ab, _ = compile_events([e_speech, e_pause], DEFAULT_OPERATOR_REGISTRY)
    ba, _ = compile_events([e_pause, e_speech], DEFAULT_OPERATOR_REGISTRY)
    assert not np.array_equal(ab, ba)


# --------------------------------------------------------------------------
# IR replay (spec §9)
# --------------------------------------------------------------------------

def test_ir_replay_matches_original():
    sig = np.concatenate([_tone(150.0, 400, sweep=100.0), _silence(350)])
    unit = _compile(sig)
    replay = AudioCompiler().compile_ir(unit.audio_ir)
    assert np.array_equal(unit.versor, replay.versor)
    assert unit.ir_sha256 == replay.ir_sha256
    assert unit.projection_sha256 == replay.projection_sha256


# --------------------------------------------------------------------------
# A-6 — trace hygiene
# --------------------------------------------------------------------------

def test_a6_evidence_trace_has_no_pcm():
    sig = _tone(180.0, 300)
    unit = _compile(sig)
    trace = audio_evidence_trace(unit)
    # No ndarray / raw-bytes payloads — only hashes, ids, scalars.
    for value in trace.values():
        assert not isinstance(value, (np.ndarray, bytes, bytearray))
    assert trace["merge_key"] == list(unit.merge_key)
    assert "samples" not in trace


# --------------------------------------------------------------------------
# Operator lawfulness — elliptic planes only
# --------------------------------------------------------------------------

def test_default_registry_uses_only_elliptic_planes():
    for spec in DEFAULT_OPERATOR_REGISTRY.specs.values():
        assert spec.blade_index in ELLIPTIC_PLANES


def test_non_elliptic_operator_is_rejected():
    with pytest.raises(ValueError):
        OperatorSpec("bad", "x", "B_BAD", 9, 64, (), 768)  # blade 9 = e1e5 (hyperbolic)


def test_build_elliptic_rotor_is_unit_versor():
    for plane in ELLIPTIC_PLANES:
        r = build_elliptic_rotor(plane, theta_q=137)
        assert versor_condition(r) < 1e-6


def test_empty_event_stream_yields_identity_versor():
    v, vc = compile_events([], DEFAULT_OPERATOR_REGISTRY)
    assert vc < 1e-6
    expected = np.zeros(32, dtype=np.float32)
    expected[0] = 1.0
    assert np.array_equal(v, expected)
