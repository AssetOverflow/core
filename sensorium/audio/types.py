"""
sensorium/audio/types.py — Typed AudioIR for the CORE-native audio compiler.

ADR-0181 §2 / spec §2. The IR is built from typed spans and events, never
from raw frames or mel bins. Every dataclass is frozen and slotted so the
compiler path is immutable and hashable, matching CORE's trace-first
epistemology.

A signal compiles to exactly one AudioCompilationUnit — the object the audio
adapter writes into its thread-local Delta-CRDT arena (ADR-0181 §2.1). The
unit carries no PCM: only the layered checksum chain, the (32,) versor, and
the content-addressed merge key (ADR-0181 §2.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

TokenKind = Literal[
    "silence", "voiced", "unvoiced", "onset",
    "energy_bin", "pitch_candidates", "spectral_bin",
]


@dataclass(frozen=True, slots=True)
class AudioSignal:
    """Canonical mono float32 signal + provenance hashes (spec §3)."""
    samples: np.ndarray        # canonical mono float32
    sample_rate: int           # canonical rate, e.g. 24_000
    start_ms: int
    end_ms: int
    source_sha256: str         # hash of the original input bytes
    canonical_sha256: str      # hash of the canonical float32 bytes


@dataclass(frozen=True, slots=True)
class PitchCandidate:
    cents_q: int               # quantized cents (25-cent bins)
    prob_q: int                # 0..255


@dataclass(frozen=True, slots=True)
class AudioToken:
    kind: TokenKind
    start_hop: int
    end_hop: int
    value_q: tuple[int, ...]   # canonical quantized payload


@dataclass(frozen=True, slots=True)
class AuditoryEvent:
    """A typed auditory event. ``attrs`` are quantized ints or short strings
    so the event serializes deterministically into the IR hash."""
    event_type: str
    start_hop: int
    end_hop: int
    attrs: tuple[tuple[str, int | str], ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AudioIR:
    speech_spans:      tuple[AuditoryEvent, ...]
    pause_spans:       tuple[AuditoryEvent, ...]
    prosody_arcs:      tuple[AuditoryEvent, ...]
    turn_events:       tuple[AuditoryEvent, ...]
    non_speech_events: tuple[AuditoryEvent, ...]
    content_anchors:   tuple[AuditoryEvent, ...]
    ir_sha256:         str


@dataclass(frozen=True, slots=True)
class AudioCompilationUnit:
    """One compiled chunk — the Delta-CRDT delta (ADR-0181 §2.1).

    ``versor`` is the (32,) float32 Cl(4,1) multivector that crosses the
    ProjectionHead boundary. ``audio_ir`` is retained for deterministic
    IR-replay (spec §9); it is evidence, never re-hashed into the projection.
    """
    canonical_sha256:     str
    ir_sha256:            str
    pack_id:              str
    pack_manifest_sha256: str
    projection_sha256:    str
    versor:               np.ndarray   # (32,) float32
    versor_condition:     float
    audio_ir:             AudioIR

    @property
    def merge_key(self) -> tuple[str, str, str]:
        """Content-addressed CRDT merge / dedup key (ADR-0181 §2.2)."""
        return (self.canonical_sha256, self.ir_sha256, self.projection_sha256)
