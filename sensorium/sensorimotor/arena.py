"""Sensorimotor CRDT wrappers."""

from __future__ import annotations

from dataclasses import dataclass

from sensorium.compiler.arena import LocalArena
from sensorium.compiler.delta import ContentAddressedDelta, merge_deltas
from sensorium.compiler.trace import merge_trace_hash
from sensorium.sensorimotor.trace import sensorimotor_evidence_trace
from sensorium.sensorimotor.types import SensorimotorCompilationUnit


@dataclass(frozen=True, slots=True)
class SensorimotorDelta:
    _inner: ContentAddressedDelta[SensorimotorCompilationUnit]

    @classmethod
    def from_units(
        cls,
        units: tuple[SensorimotorCompilationUnit, ...] | list[SensorimotorCompilationUnit],
    ) -> "SensorimotorDelta":
        return cls(ContentAddressedDelta.from_units(units))

    @property
    def units(self) -> tuple[SensorimotorCompilationUnit, ...]:
        return self._inner.units

    def join(self, other: "SensorimotorDelta") -> "SensorimotorDelta":
        return SensorimotorDelta(self._inner.join(other._inner))

    @property
    def merge_keys(self) -> tuple[tuple[str, str, str], ...]:
        return self._inner.merge_keys

    def __len__(self) -> int:
        return len(self._inner)


class SensorimotorArena:
    __slots__ = ("_arena",)

    def __init__(self) -> None:
        self._arena: LocalArena[SensorimotorCompilationUnit] = LocalArena()

    def push(self, unit: SensorimotorCompilationUnit) -> None:
        self._arena.push(unit)

    def snapshot(self) -> SensorimotorDelta:
        return SensorimotorDelta(self._arena.snapshot())


def merge_sensorimotor_deltas(
    deltas: list[SensorimotorDelta] | tuple[SensorimotorDelta, ...],
) -> SensorimotorDelta:
    return SensorimotorDelta(merge_deltas(delta._inner for delta in deltas))


def sensorimotor_merge_trace_hash(delta: SensorimotorDelta) -> str:
    return merge_trace_hash(delta._inner, sensorimotor_evidence_trace)
