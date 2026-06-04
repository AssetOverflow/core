"""Local, non-draining arenas for compiled sensorium units."""

from __future__ import annotations

from typing import Generic, TypeVar

from sensorium.compiler.delta import ContentAddressedDelta
from sensorium.compiler.protocol import CompilationUnitLike

U = TypeVar("U", bound=CompilationUnitLike)


class LocalArena(Generic[U]):
    """Share-nothing accumulation arena.

    Snapshot is deliberately non-draining; flush/GC belongs to the merge owner.
    """

    __slots__ = ("_units",)

    def __init__(self) -> None:
        self._units: list[U] = []

    def push(self, unit: U) -> None:
        self._units.append(unit)

    def is_empty(self) -> bool:
        return not self._units

    def snapshot(self) -> ContentAddressedDelta[U]:
        return ContentAddressedDelta.from_units(self._units)

    def __len__(self) -> int:
        return len(self._units)
