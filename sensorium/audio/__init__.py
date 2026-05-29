"""
sensorium.audio — CORE-native deterministic audio compiler (ADR-0181, PR-2).

Audio enters CORE as a compiler, not an embedding bridge: canonical waveform
→ typed AudioIR → (32,) float32 Cl(4,1) versor, fully deterministic and
replayable. Each compiled chunk is one AudioCompilationUnit — the Delta-CRDT
delta the audio adapter writes into its thread-local arena (ADR-0181 §2.1).

PR-2 ships the deterministic substrate; pack artifacts + the AudioProjectionHead
adapter land in PR-3; evals in PR-4; CRDT arena/merge wiring in PR-5
(`sensorium.audio.arena`); teacher/shadow lanes in PR-6
(`sensorium.audio.teachers` — typed hints only, never substrate).
"""

from sensorium.audio.arena import (
    AudioArena,
    AudioDelta,
    audio_merge_trace_hash,
    merge_audio_deltas,
    reset_thread_local_audio_arena,
    thread_local_audio_arena,
)
from sensorium.audio.compiler import AudioCompiler, compile_events
from sensorium.audio.operators import (
    DEFAULT_OPERATOR_REGISTRY,
    AudioOperatorRegistry,
    OperatorSpec,
    build_elliptic_rotor,
)
from sensorium.audio.teachers import (
    AudioTeacher,
    StubTranscriptTeacher,
    TeacherHint,
    TeacherLaneSpec,
    TeacherUnavailable,
    attach_teacher_hints,
    is_lane_available,
    KNOWN_TEACHER_LANES,
    load_teacher,
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
    "AudioArena",
    "AudioDelta",
    "audio_merge_trace_hash",
    "merge_audio_deltas",
    "reset_thread_local_audio_arena",
    "thread_local_audio_arena",
    "AudioCompiler",
    "compile_events",
    "AudioOperatorRegistry",
    "OperatorSpec",
    "DEFAULT_OPERATOR_REGISTRY",
    "build_elliptic_rotor",
    "audio_evidence_trace",
    "AudioTeacher",
    "StubTranscriptTeacher",
    "TeacherHint",
    "TeacherLaneSpec",
    "TeacherUnavailable",
    "attach_teacher_hints",
    "is_lane_available",
    "KNOWN_TEACHER_LANES",
    "load_teacher",
    "AudioCompilationUnit",
    "AudioIR",
    "AudioSignal",
    "AudioToken",
    "AuditoryEvent",
    "PitchCandidate",
]
