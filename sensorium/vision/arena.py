"""Vision Delta-CRDT wrappers over the shared compiler substrate."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from sensorium.compiler.arena import LocalArena
from sensorium.compiler.delta import ContentAddressedDelta, merge_deltas
from sensorium.compiler.trace import merge_trace_hash
from sensorium.vision.trace import vision_evidence_trace
from sensorium.vision.types import VisionCompilationUnit

MergeKey = tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class VisionDelta:
    _inner: ContentAddressedDelta[VisionCompilationUnit]

    @classmethod
    def from_units(
        cls,
        units: tuple[VisionCompilationUnit, ...] | list[VisionCompilationUnit],
    ) -> "VisionDelta":
        return cls(ContentAddressedDelta.from_units(units))

    @property
    def units(self) -> tuple[VisionCompilationUnit, ...]:
        return self._inner.units

    def join(self, other: "VisionDelta") -> "VisionDelta":
        return VisionDelta(self._inner.join(other._inner))

    @property
    def merge_keys(self) -> tuple[MergeKey, ...]:
        return self._inner.merge_keys

    def __len__(self) -> int:
        return len(self._inner)


class VisionArena:
    __slots__ = ("_arena",)

    def __init__(self) -> None:
        self._arena: LocalArena[VisionCompilationUnit] = LocalArena()

    def push(self, unit: VisionCompilationUnit) -> None:
        self._arena.push(unit)

    def is_empty(self) -> bool:
        return self._arena.is_empty()

    def snapshot(self) -> VisionDelta:
        return VisionDelta(self._arena.snapshot())

    def __len__(self) -> int:
        return len(self._arena)


_THREAD_LOCAL = threading.local()


def thread_local_vision_arena() -> VisionArena:
    arena = getattr(_THREAD_LOCAL, "vision_arena", None)
    if arena is None:
        arena = VisionArena()
        _THREAD_LOCAL.vision_arena = arena
    return arena


def reset_thread_local_vision_arena() -> None:
    if hasattr(_THREAD_LOCAL, "vision_arena"):
        del _THREAD_LOCAL.vision_arena


def merge_vision_deltas(deltas: list[VisionDelta] | tuple[VisionDelta, ...]) -> VisionDelta:
    return VisionDelta(merge_deltas(delta._inner for delta in deltas))


def vision_merge_trace_hash(merged: VisionDelta) -> str:
    return merge_trace_hash(merged._inner, vision_evidence_trace)
