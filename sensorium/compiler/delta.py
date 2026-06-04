"""Content-addressed Delta-CRDT primitives for sensorium compilation units."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Iterable, TypeVar

from sensorium.compiler.protocol import CompilationUnitLike, MergeKey

U = TypeVar("U", bound=CompilationUnitLike)


def _canonicalize(units: Iterable[U]) -> tuple[U, ...]:
    """Sort by merge key and drop exact duplicate keys."""
    ordered = sorted(units, key=lambda u: u.merge_key)
    deduped: list[U] = []
    last_key: MergeKey | None = None
    for unit in ordered:
        if unit.merge_key != last_key:
            deduped.append(unit)
            last_key = unit.merge_key
    return tuple(deduped)


@dataclass(frozen=True, slots=True)
class ContentAddressedDelta(Generic[U]):
    """Canonical join-semilattice element for compiled modality units."""

    units: tuple[U, ...]

    @classmethod
    def from_units(cls, units: Iterable[U]) -> "ContentAddressedDelta[U]":
        return cls(_canonicalize(units))

    def join(self, other: "ContentAddressedDelta[U]") -> "ContentAddressedDelta[U]":
        return ContentAddressedDelta.from_units((*self.units, *other.units))

    @property
    def merge_keys(self) -> tuple[MergeKey, ...]:
        return tuple(unit.merge_key for unit in self.units)

    def __len__(self) -> int:
        return len(self.units)


def merge_deltas(deltas: Iterable[ContentAddressedDelta[U]]) -> ContentAddressedDelta[U]:
    """Fold deltas by one canonical union operation."""
    units: list[U] = []
    for delta in deltas:
        units.extend(delta.units)
    return ContentAddressedDelta.from_units(units)
