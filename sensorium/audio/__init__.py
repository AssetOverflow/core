"""
sensorium.audio — CORE-native deterministic audio compiler (ADR-0181, PR-2).

Audio enters CORE as a compiler, not an embedding bridge: canonical waveform
→ typed AudioIR → (32,) float32 Cl(4,1) versor, fully deterministic and
replayable. Each compiled chunk is one AudioCompilationUnit — the Delta-CRDT
delta the audio adapter writes into its thread-local arena (ADR-0181 §2.1).

PR-2 ships the deterministic substrate only. Pack artifacts + the
AudioProjectionHead adapter land in PR-3; evals in PR-4; CRDT wiring in PR-5.
"""

from sensorium.audio.compiler import AudioCompiler, compile_events
from sensorium.audio.operators import (
    DEFAULT_OPERATOR_REGISTRY,
    AudioOperatorRegistry,
    OperatorSpec,
    build_elliptic_rotor,
)
from sensorium.audio.trace import audio_evidence_trace
from sensorium.audio.types import (
    AudioCompilationUnit,
    AudioIR,
    AudioSignal,
    AudioToken,
    AuditoryEvent,
    PitchCandidate,
)

__all__ = [
    "AudioCompiler",
    "compile_events",
    "AudioOperatorRegistry",
    "OperatorSpec",
    "DEFAULT_OPERATOR_REGISTRY",
    "build_elliptic_rotor",
    "audio_evidence_trace",
    "AudioCompilationUnit",
    "AudioIR",
    "AudioSignal",
    "AudioToken",
    "AuditoryEvent",
    "PitchCandidate",
]
