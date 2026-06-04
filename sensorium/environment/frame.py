"""Deterministic environmental observation frames.

An ObservationFrame is a traceable bundle of already-compiled afferent units.
It is not a fusion layer and it never accepts efferent action commands as
observation evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from sensorium.audio.checksum import sha256_json
from sensorium.compiler.protocol import CompilationUnitLike, MergeKey

_UNSAFE_ATTRS = ("pixels", "samples", "pcm", "waveform", "raw_bytes", "action_trace")


def _reject_unsafe_unit(unit: CompilationUnitLike) -> None:
    if bool(getattr(unit, "efferent", False)):
        raise ValueError("efferent action traces are not afferent observation units")
    if str(getattr(unit, "pack_id", "")).startswith("motor"):
        raise ValueError("motor/efferent packs are not observation units")
    for attr in _UNSAFE_ATTRS:
        if hasattr(unit, attr):
            value = getattr(unit, attr)
            if isinstance(value, (np.ndarray, bytes, bytearray)):
                raise TypeError(f"unsafe observation payload on unit: {attr}")


def _unit_record(unit: CompilationUnitLike) -> dict[str, object]:
    _reject_unsafe_unit(unit)
    return {
        "merge_key": list(unit.merge_key),
        "canonical_sha256": unit.canonical_sha256,
        "ir_sha256": unit.ir_sha256,
        "pack_id": unit.pack_id,
        "pack_manifest_sha256": unit.pack_manifest_sha256,
        "projection_sha256": unit.projection_sha256,
        "versor_condition": float(unit.versor_condition),
    }


def _canonical_units(units: Iterable[CompilationUnitLike]) -> tuple[CompilationUnitLike, ...]:
    ordered = sorted(tuple(units), key=lambda u: u.merge_key)
    deduped: list[CompilationUnitLike] = []
    last_key: MergeKey | None = None
    for unit in ordered:
        if unit.merge_key != last_key:
            deduped.append(unit)
            last_key = unit.merge_key
    return tuple(deduped)


@dataclass(frozen=True, slots=True)
class ObservationFrame:
    """A deterministic environmental slice over afferent compiled units."""

    frame_id: str
    monotonic_tick: int
    source_clock: str
    units: tuple[CompilationUnitLike, ...]
    causal_parent_ids: tuple[str, ...]
    environment_sha256: str
    trace_hash: str


def build_observation_frame(
    *,
    monotonic_tick: int,
    source_clock: str,
    units: Iterable[CompilationUnitLike],
    causal_parent_ids: tuple[str, ...] = (),
) -> ObservationFrame:
    if monotonic_tick < 0:
        raise ValueError("monotonic_tick must be non-negative")
    canonical_units = _canonical_units(units)
    unit_records = [_unit_record(unit) for unit in canonical_units]
    env_payload = {
        "monotonic_tick": int(monotonic_tick),
        "source_clock": str(source_clock),
        "causal_parent_ids": list(causal_parent_ids),
        "unit_records": unit_records,
    }
    environment_sha256 = sha256_json(env_payload)
    trace_hash = sha256_json({
        "kind": "ObservationFrame",
        "environment_sha256": environment_sha256,
        "unit_merge_keys": [record["merge_key"] for record in unit_records],
    })
    frame_id = sha256_json({
        "kind": "ObservationFrame.id",
        "monotonic_tick": int(monotonic_tick),
        "source_clock": str(source_clock),
        "trace_hash": trace_hash,
    })
    return ObservationFrame(
        frame_id=frame_id,
        monotonic_tick=int(monotonic_tick),
        source_clock=str(source_clock),
        units=canonical_units,
        causal_parent_ids=tuple(causal_parent_ids),
        environment_sha256=environment_sha256,
        trace_hash=trace_hash,
    )
