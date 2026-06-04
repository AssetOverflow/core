"""
sensorium/audio/arena.py — audio Delta-CRDT arena + merge kernel (ADR-0181 PR-5).

Wires `AudioCompilationUnit`s into the Delta-CRDT substrate (ADR-0180 §2.1/§2.2):
each compiled chunk is one delta; the audio adapter accumulates units in a
thread-local `AudioArena` (share-nothing, never writes global state); the merge
kernel folds arena snapshots into one content-addressed, deduplicated, totally
ordered set keyed by the unit's `merge_key`
(`canonical_sha256, ir_sha256, projection_sha256`).

This is the **Python-layer mirror** of the Rust substrate
(`core-rs/src/vault.rs` — `LocalArena` / `SemilatticeDelta` / `merge_kernel`,
ADR-0180 §4.1): same content-addressed sort + byte-identical dedup, so the two
stay in parity when the Rust↔Python binding lands (ADR-0180 §1.5.5 — deferred to
a follow-up; the substrate works on the pure-CPU path first). Audio is the first
concrete exerciser of ADR-0180 (ADR-0181 §3.1).

The merge result is **permutation- and duplicate-invariant** — the property
ADR-0180 §4.3 / ADR-0181 §4.2 (A-2, A-3) require:

    hash(Sequential_Ingest) == hash(Concurrent_CRDT_Ingest)

Idempotence is structural, not asserted (ADR-0181 §2.2): identical canonical
bytes under an identical pack produce an identical `merge_key`, so the join
deduplicates them by construction.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from sensorium.compiler.arena import LocalArena
from sensorium.compiler.delta import ContentAddressedDelta, merge_deltas
from sensorium.compiler.trace import merge_trace_hash
from sensorium.audio.trace import audio_evidence_trace
from sensorium.audio.types import AudioCompilationUnit

MergeKey = tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class AudioDelta:
    """A canonical, order-invariant set of compiled audio chunks (ADR-0181 §2.2).

    Always held in content-addressed `merge_key` order with byte-identical
    duplicates removed, so it is a canonical join-semilattice element regardless
    of insertion order. Mirrors `core-rs` `Delta`.
    """

    _inner: ContentAddressedDelta[AudioCompilationUnit]

    @classmethod
    def from_units(
        cls,
        units: tuple[AudioCompilationUnit, ...] | list[AudioCompilationUnit],
    ) -> AudioDelta:
        return cls(ContentAddressedDelta.from_units(units))

    @property
    def units(self) -> tuple[AudioCompilationUnit, ...]:
        return self._inner.units

    def join(self, other: AudioDelta) -> AudioDelta:
        """Join semilattice op: commutative, associative, idempotent under
        content-addressed equality (ADR-0180 §2.2)."""
        return AudioDelta(self._inner.join(other._inner))

    @property
    def merge_keys(self) -> tuple[MergeKey, ...]:
        return self._inner.merge_keys

    def __len__(self) -> int:
        return len(self._inner)


class AudioArena:
    """Thread-local, share-nothing accumulation arena for the audio adapter
    (ADR-0180 §2.1).

    Push compiled units lock-free; nothing is ever written to global state from
    an arena. `snapshot` emits a canonical, order-invariant `AudioDelta` and is
    **non-destructive** — flush/GC is the Merge Kernel's concern, so a delayed
    merge (the §3.2 eventual-consistency window) cannot lose a unit. Mirrors
    `core-rs` `LocalArena`.
    """

    __slots__ = ("_arena",)

    def __init__(self) -> None:
        self._arena: LocalArena[AudioCompilationUnit] = LocalArena()

    def push(self, unit: AudioCompilationUnit) -> None:
        self._arena.push(unit)

    def is_empty(self) -> bool:
        return self._arena.is_empty()

    def snapshot(self) -> AudioDelta:
        return AudioDelta(self._arena.snapshot())

    def __len__(self) -> int:
        return len(self._arena)


_THREAD_LOCAL = threading.local()


def thread_local_audio_arena() -> AudioArena:
    """The calling thread's audio arena (ADR-0180 §2.1: each active adapter gets
    a thread-local arena). Created on first access per thread; never shared
    across threads, so it needs no lock."""
    arena = getattr(_THREAD_LOCAL, "audio_arena", None)
    if arena is None:
        arena = AudioArena()
        _THREAD_LOCAL.audio_arena = arena
    return arena


def reset_thread_local_audio_arena() -> None:
    """Drop the calling thread's arena (flush/test helper). Pools reuse threads,
    so callers that want a fresh arena per task must reset first."""
    if hasattr(_THREAD_LOCAL, "audio_arena"):
        del _THREAD_LOCAL.audio_arena


def merge_audio_deltas(deltas: list[AudioDelta] | tuple[AudioDelta, ...]) -> AudioDelta:
    """The Merge Kernel (ADR-0180 §2.2): fold arena deltas into one content-
    addressed, deduplicated, totally ordered `AudioDelta`.

    Implemented as a single canonicalisation of the union rather than a
    `fold(join)` chain; `tests/test_audio_crdt_merge.py` pins that the two are
    equal, so the cheap path can never silently diverge from the semilattice
    fold. Permutation- and duplicate-invariant — the property §4.3's
    `hash(Sequential) == hash(Concurrent)` rides on.
    """
    return AudioDelta(merge_deltas(delta._inner for delta in deltas))


def audio_merge_trace_hash(merged: AudioDelta) -> str:
    """Deterministic, PCM-free trace hash over a merged `AudioDelta` — the
    `sequential == concurrent` anchor (ADR-0181 §3.1, §4.2 A-3/A-6).

    The payload is the per-unit evidence trace (no waveform — ADR-0180 §1.5.5)
    in canonical `merge_key` order. Identical content in any arrival order yields
    the same hash; distinct content yields a different hash. Determinism here is
    order-invariance on a fixed platform; the compiler's A-1 gate owns
    cross-platform float stability of the underlying versors.
    """
    return merge_trace_hash(merged._inner, audio_evidence_trace)
