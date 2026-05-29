"""
sensorium/audio/teachers.py — teacher / shadow lanes (ADR-0181 PR-6).

Teachers **label or align**; they never define the substrate and never fold
embeddings into the main versor path (eval-plan §4, verbatim):

    Use teachers to label or align.
    Never let teachers define the substrate.
    Never fold teacher embeddings directly into the main versor path.
    Only admit teacher outputs through typed, versioned, checksumed hints.

A teacher emits typed, versioned, checksummed `TeacherHint`s. The only admission
path is `attach_teacher_hints`, which appends them to the IR's `content_anchors`
as `content.*` events. `content.*` is **not** an operator-registry key, so
`compile_events` skips them (compiler.py: "Events whose type has no operator are
skipped"): a hint contributes IR evidence and a different `ir_sha256`, but the
**versor and `projection_sha256` are byte-identical** with or without it. That is
the structural guarantee that teachers are shadow, proven failably in
`tests/test_audio_teachers.py`.

Real model lanes (Whisper / NeMo / CLAP / EnCodec) are declared and gated behind
optional extras; their adapters are import-guarded and degrade gracefully when
the extra is absent. The deterministic `StubTranscriptTeacher` is the reference
implementation of the contract and needs no model weights.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, replace
from typing import Callable, Literal, Protocol, Sequence, runtime_checkable

from sensorium.audio.checksum import sha256_json
from sensorium.audio.parser import ir_sha256_of
from sensorium.audio.types import AudioIR, AudioSignal, AuditoryEvent

HintType = Literal["transcript", "alignment", "sound_event", "lang_id", "reconstruction"]

# The IR namespace teacher hints live under. Must never collide with an operator
# key (speech.* / pause.* / prosody.* / turn.* / nonspeech.*), or a hint would
# lower to a rotor and become substrate.
CONTENT_ANCHOR_PREFIX = "content"


@dataclass(frozen=True, slots=True)
class TeacherHint:
    """A typed, versioned, checksummed teacher annotation (eval-plan §4).

    `payload` is typed/quantized ints or short strings — never a raw embedding.
    `hint_sha256` checksums the canonical payload so the hint is content-addressed
    and tamper-evident.
    """

    lane_id: str
    lane_version: str
    hint_type: HintType
    start_hop: int
    end_hop: int
    payload: tuple[tuple[str, int | str], ...]
    confidence_q: int          # 0..255
    hint_sha256: str

    @classmethod
    def make(
        cls,
        *,
        lane_id: str,
        lane_version: str,
        hint_type: HintType,
        start_hop: int,
        end_hop: int,
        payload: tuple[tuple[str, int | str], ...] = (),
        confidence_q: int = 0,
    ) -> TeacherHint:
        digest = sha256_json(
            {
                "lane_id": lane_id,
                "lane_version": lane_version,
                "hint_type": hint_type,
                "start_hop": start_hop,
                "end_hop": end_hop,
                "payload": [list(p) for p in payload],
                "confidence_q": confidence_q,
            }
        )
        return cls(
            lane_id=lane_id,
            lane_version=lane_version,
            hint_type=hint_type,
            start_hop=start_hop,
            end_hop=end_hop,
            payload=payload,
            confidence_q=confidence_q,
            hint_sha256=digest,
        )

    @property
    def evidence_id(self) -> str:
        return f"{self.lane_id}:{self.lane_version}:{self.hint_sha256}"

    def to_anchor(self) -> AuditoryEvent:
        """Lower to a `content.*` IR anchor — evidence only, never a rotor."""
        attrs: tuple[tuple[str, int | str], ...] = (
            ("lane_id", self.lane_id),
            ("lane_version", self.lane_version),
            ("hint_type", self.hint_type),
            ("confidence_q", self.confidence_q),
            *self.payload,
        )
        return AuditoryEvent(
            event_type=f"{CONTENT_ANCHOR_PREFIX}.{self.hint_type}",
            start_hop=self.start_hop,
            end_hop=self.end_hop,
            attrs=attrs,
            evidence_ids=(self.evidence_id,),
        )


@runtime_checkable
class AudioTeacher(Protocol):
    """A shadow-lane annotator. `annotate` must be pure on the signal — no
    cross-modal or global state — mirroring the compiler's determinism so a hint
    never depends on ingest order."""

    lane_id: str
    lane_version: str

    def annotate(self, signal: AudioSignal) -> tuple[TeacherHint, ...]: ...


def attach_teacher_hints(ir: AudioIR, hints: Sequence[TeacherHint]) -> AudioIR:
    """Admit teacher hints into an IR as `content_anchors` (the ONLY admission
    path). Returns a NEW AudioIR with `ir_sha256` recomputed; the input is
    unchanged (immutable). The versor is unaffected — `content.*` anchors carry
    no operator (proven in tests)."""
    if not hints:
        return ir
    anchors = tuple(h.to_anchor() for h in hints)
    merged = tuple(
        sorted(
            (*ir.content_anchors, *anchors),
            key=lambda e: (e.start_hop, e.end_hop, e.event_type, e.evidence_ids),
        )
    )
    augmented = replace(ir, content_anchors=merged)
    return replace(augmented, ir_sha256=ir_sha256_of(augmented))


# ---------------------------------------------------------------------------
# Reference teacher (no model weights) — the working contract instance.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StubTranscriptTeacher:
    """Deterministic reference teacher. Emits one whole-signal transcript hint
    whose token is derived from the canonical hash — pure on the signal, so the
    same signal always yields the same hint. Exercises the contract end-to-end
    without a real ASR dependency."""

    lane_id: str = "stub_transcript"
    lane_version: str = "stub-v1"
    hop_samples: int = 240  # 10 ms @ 24 kHz

    def annotate(self, signal: AudioSignal) -> tuple[TeacherHint, ...]:
        n_hops = max(1, int(len(signal.samples) // self.hop_samples))
        token = signal.canonical_sha256[:8]
        return (
            TeacherHint.make(
                lane_id=self.lane_id,
                lane_version=self.lane_version,
                hint_type="transcript",
                start_hop=0,
                end_hop=n_hops,
                payload=(("token", token),),
                confidence_q=128,
            ),
        )


# ---------------------------------------------------------------------------
# Real model lanes — declared, gated, import-guarded (eval-plan §4 table).
# ---------------------------------------------------------------------------


class TeacherUnavailable(RuntimeError):
    """Raised when a declared teacher lane cannot be constructed — the extra is
    not installed, or its adapter has not been wired yet."""


@dataclass(frozen=True, slots=True)
class TeacherLaneSpec:
    lane_id: str
    extra: str           # pip extra that provides the model
    probe_module: str    # importable module used to detect availability
    role: str            # what the lane is good for (never substrate)
    builder: Callable[[], AudioTeacher] | None = None  # None until an adapter lands


# eval-plan §4: best role in CORE / why not the substrate. Adapters are deferred
# until the extra + weights are present; the lane is declared and gated now.
KNOWN_TEACHER_LANES: dict[str, TeacherLaneSpec] = {
    "whisper": TeacherLaneSpec(
        "whisper", "audio-whisper", "whisper",
        "offline transcript evidence, weak lexical labels, language ID",
    ),
    "nemo": TeacherLaneSpec(
        "nemo", "audio-nemo", "nemo",
        "timestamp/alignment teacher + streaming transcript evidence",
    ),
    "clap": TeacherLaneSpec(
        "clap", "audio-clap", "laion_clap",
        "coarse sound-event labels, audio-text alignment",
    ),
    "encodec": TeacherLaneSpec(
        "encodec", "audio-encodec", "encodec",
        "reconstruction shadow lane, transport, future speech-to-speech",
    ),
}


def is_lane_available(lane_id: str) -> bool:
    """True iff the lane's optional dependency is importable. Does not import it."""
    spec = KNOWN_TEACHER_LANES.get(lane_id)
    if spec is None:
        return False
    return importlib.util.find_spec(spec.probe_module) is not None


def load_teacher(lane_id: str) -> AudioTeacher:
    """Construct a teacher for a declared lane, or fail loudly with guidance.

    Raises `ValueError` for an unknown lane, `TeacherUnavailable` when the extra
    is missing or no adapter is wired yet. Never returns a partially-built or
    silent-fallback teacher — a teacher must be a real, typed-hint producer or
    nothing at all.
    """
    spec = KNOWN_TEACHER_LANES.get(lane_id)
    if spec is None:
        known = ", ".join(sorted(KNOWN_TEACHER_LANES))
        raise ValueError(f"unknown teacher lane {lane_id!r}; known lanes: {known}")
    if spec.builder is None:
        raise TeacherUnavailable(
            f"teacher lane {lane_id!r} is declared but its adapter is not wired "
            f"yet (install `{spec.extra}` and register a builder). "
            f"Role: {spec.role}."
        )
    if not is_lane_available(lane_id):
        raise TeacherUnavailable(
            f"teacher lane {lane_id!r} requires the optional extra "
            f"`{spec.extra}` (module {spec.probe_module!r} not importable)."
        )
    return spec.builder()
