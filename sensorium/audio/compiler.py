"""
sensorium/audio/compiler.py — the deterministic audio compiler (spec §1, §7, §9).

Pipeline: canonical signal → frame grid → lexer → typed AudioIR → canonical
event ordering → rotor lowering → versor composition → AudioCompilationUnit.

The ``compile_events`` fold is the **serialization barrier** of ADR-0181 §2.1:
it composes non-commutative rotors serially, in canonical order, and the only
thing that crosses into the Delta-CRDT merge layer is the order-invariant
AudioCompilationUnit (keyed by its content-addressed merge key).

Strict invariant (spec §9 / ADR-0181 §4.3): same canonical bytes + same pack
⇒ same IR ⇒ same versor ⇒ same projection hash ⇒ same merge key.
"""

from __future__ import annotations

import numpy as np

from algebra.cl41 import geometric_product
from algebra.versor import unitize_versor, versor_condition
from sensorium.audio.canonical import CANONICAL_SAMPLE_RATE, canonicalize
from sensorium.audio.checksum import sha256_array
from sensorium.audio.frames import frame_signal
from sensorium.audio.lexer import lex
from sensorium.audio.operators import (
    DEFAULT_OPERATOR_REGISTRY,
    AudioOperatorRegistry,
    build_elliptic_rotor,
)
from sensorium.audio.parser import parse
from sensorium.audio.types import (
    AudioCompilationUnit,
    AudioIR,
    AudioSignal,
    AuditoryEvent,
)

CL41_DIM = 32
VERSOR_CONDITION_MAX = 1e-6

# Manifest event precedence (spec §6.1 [ordering]).
_PRECEDENCE = ("channel", "pause", "speech", "prosody", "turn", "non_speech", "content_anchor")
_PREFIX_TO_CATEGORY = {
    "pause": "pause", "speech": "speech", "prosody": "prosody",
    "turn": "turn", "nonspeech": "non_speech", "channel": "channel",
}


def _category(event_type: str) -> str:
    prefix = event_type.split(".", 1)[0]
    return _PREFIX_TO_CATEGORY.get(prefix, "content_anchor")


def canonical_event_order(ir: AudioIR) -> list[AuditoryEvent]:
    """Flatten the IR into a single canonically-ordered event sequence.

    Stable key: (precedence rank, start_hop, end_hop, event_type). This is the
    order ``compile_events`` folds in — deterministic for a fixed IR.
    """
    events = [
        *ir.pause_spans, *ir.speech_spans, *ir.prosody_arcs,
        *ir.turn_events, *ir.non_speech_events, *ir.content_anchors,
    ]
    rank = {name: i for i, name in enumerate(_PRECEDENCE)}
    return sorted(
        events,
        key=lambda e: (rank.get(_category(e.event_type), len(_PRECEDENCE)),
                       e.start_hop, e.end_hop, e.event_type),
    )


def compile_events(
    events: list[AuditoryEvent],
    registry: AudioOperatorRegistry,
) -> tuple[np.ndarray, float]:
    """SERIALIZATION BARRIER (ADR-0181 §2.1).

    Fold the canonical-ordered events into a single unit versor. Events whose
    type has no operator are skipped (they contribute evidence to the IR but
    no rotor). Returns (versor float32, versor_condition).
    """
    v = np.zeros(CL41_DIM, dtype=np.float64)
    v[0] = 1.0
    for ev in events:
        if ev.event_type not in registry:
            continue
        spec = registry[ev.event_type]
        theta_q = spec.theta_q_from_event(ev)
        r = build_elliptic_rotor(spec.blade_index, theta_q)
        v = geometric_product(v, r)
        v = unitize_versor(v)
    vc = float(versor_condition(v))
    if vc >= VERSOR_CONDITION_MAX:
        raise ValueError(
            f"audio compilation failed versor check: versor_condition={vc:.3e} "
            f">= {VERSOR_CONDITION_MAX:.0e}"
        )
    return v.astype(np.float32), vc


class AudioCompiler:
    """Deterministic compiler from raw waveform to an AudioCompilationUnit."""

    def __init__(
        self,
        registry: AudioOperatorRegistry = DEFAULT_OPERATOR_REGISTRY,
        pack_id: str = "audio_core_v1",
        *,
        target_sr: int = CANONICAL_SAMPLE_RATE,
    ) -> None:
        self._registry = registry
        self._pack_id = pack_id
        self._target_sr = target_sr
        self._manifest_sha256 = registry.manifest_sha256()

    def compile(
        self,
        samples: np.ndarray,
        sample_rate: int,
        *,
        fir: np.ndarray | None = None,
    ) -> AudioCompilationUnit:
        signal = canonicalize(samples, sample_rate, target_sr=self._target_sr, fir=fir)
        return self._compile_signal(signal)

    def compile_signal(self, signal: AudioSignal) -> AudioCompilationUnit:
        """Compile an already-canonicalised signal."""
        return self._compile_signal(signal)

    def _compile_signal(self, signal: AudioSignal) -> AudioCompilationUnit:
        frames = frame_signal(signal.samples, signal.sample_rate)
        tokens = lex(frames, signal.sample_rate)
        ir = parse(tokens, n_hops=frames.shape[0])

        versor, vc = compile_events(canonical_event_order(ir), self._registry)
        return AudioCompilationUnit(
            canonical_sha256=signal.canonical_sha256,
            ir_sha256=ir.ir_sha256,
            pack_id=self._pack_id,
            pack_manifest_sha256=self._manifest_sha256,
            projection_sha256=sha256_array(versor),
            versor=versor,
            versor_condition=vc,
            audio_ir=ir,
        )

    def compile_ir(self, ir: AudioIR) -> AudioCompilationUnit:
        """Replay: recompile a stored IR back to a versor (spec §9 IR-replay).

        ``canonical_sha256`` is not available from the IR alone; replay equality
        is asserted on the versor and ``ir_sha256`` (eval-plan §3.2).
        """
        versor, vc = compile_events(canonical_event_order(ir), self._registry)
        return AudioCompilationUnit(
            canonical_sha256="",
            ir_sha256=ir.ir_sha256,
            pack_id=self._pack_id,
            pack_manifest_sha256=self._manifest_sha256,
            projection_sha256=sha256_array(versor),
            versor=versor,
            versor_condition=vc,
            audio_ir=ir,
        )
