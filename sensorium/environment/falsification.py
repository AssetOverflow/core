"""Deterministic expected-vs-actual environmental falsification.

This module compares already-compiled afferent units. It does not compile raw
signals, decode motor commands, fuse modalities, mutate Vault state, or create a
world model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from sensorium.audio.checksum import sha256_json
from sensorium.compiler.protocol import CompilationUnitLike, MergeKey
from sensorium.environment.frame import ObservationFrame

_UNSAFE_ATTRS = ("pixels", "samples", "pcm", "waveform", "raw_bytes", "action_trace")


def _reject_unsafe_unit(unit: CompilationUnitLike) -> None:
    if bool(getattr(unit, "efferent", False)):
        raise ValueError("efferent action traces are not environmental evidence units")
    if str(getattr(unit, "pack_id", "")).startswith("motor"):
        raise ValueError("motor/efferent packs are not environmental evidence units")
    for attr in _UNSAFE_ATTRS:
        if hasattr(unit, attr):
            value = getattr(unit, attr)
            if isinstance(value, (np.ndarray, bytes, bytearray)):
                raise TypeError(f"unsafe environmental evidence payload on unit: {attr}")


def _merge_key_record(key: MergeKey) -> list[str]:
    return [str(key[0]), str(key[1]), str(key[2])]


def _unit_record(unit: CompilationUnitLike) -> dict[str, object]:
    _reject_unsafe_unit(unit)
    return {
        "merge_key": _merge_key_record(unit.merge_key),
        "canonical_sha256": unit.canonical_sha256,
        "ir_sha256": unit.ir_sha256,
        "pack_id": unit.pack_id,
        "pack_manifest_sha256": unit.pack_manifest_sha256,
        "projection_sha256": unit.projection_sha256,
        "versor_condition": float(unit.versor_condition),
    }


@dataclass(frozen=True, slots=True)
class ObservationUnitRef:
    """Slot-labelled reference to one compiled afferent unit."""

    slot_id: str
    unit: CompilationUnitLike

    def __post_init__(self) -> None:
        if not self.slot_id.strip():
            raise ValueError("ObservationUnitRef.slot_id is required")
        _reject_unsafe_unit(self.unit)

    @property
    def merge_key(self) -> MergeKey:
        return self.unit.merge_key

    def as_dict(self) -> dict[str, object]:
        return {
            "slot_id": self.slot_id,
            "unit": _unit_record(self.unit),
        }


def _canonical_refs(refs: Iterable[ObservationUnitRef]) -> tuple[ObservationUnitRef, ...]:
    ordered = sorted(tuple(refs), key=lambda r: (r.slot_id, r.merge_key))
    deduped: list[ObservationUnitRef] = []
    seen_pairs: set[tuple[str, MergeKey]] = set()
    seen_slots: dict[str, MergeKey] = {}
    for ref in ordered:
        key = (ref.slot_id, ref.merge_key)
        if key in seen_pairs:
            continue
        if ref.slot_id in seen_slots and seen_slots[ref.slot_id] != ref.merge_key:
            raise ValueError(f"conflicting units for observation slot: {ref.slot_id}")
        seen_pairs.add(key)
        seen_slots[ref.slot_id] = ref.merge_key
        deduped.append(ref)
    return tuple(deduped)


@dataclass(frozen=True, slots=True)
class ExpectedObservationFrame:
    """Replay-stable expectation over afferent observation slots."""

    expected_id: str
    monotonic_tick: int
    source_clock: str
    unit_refs: tuple[ObservationUnitRef, ...]
    causal_parent_ids: tuple[str, ...]
    expected_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "expected_id": self.expected_id,
            "monotonic_tick": self.monotonic_tick,
            "source_clock": self.source_clock,
            "unit_refs": [ref.as_dict() for ref in self.unit_refs],
            "causal_parent_ids": list(self.causal_parent_ids),
            "expected_sha256": self.expected_sha256,
        }


def build_expected_observation_frame(
    *,
    monotonic_tick: int,
    source_clock: str,
    unit_refs: Iterable[ObservationUnitRef],
    causal_parent_ids: tuple[str, ...] = (),
) -> ExpectedObservationFrame:
    if monotonic_tick < 0:
        raise ValueError("monotonic_tick must be non-negative")
    canonical_refs = _canonical_refs(unit_refs)
    payload = {
        "kind": "ExpectedObservationFrame",
        "monotonic_tick": int(monotonic_tick),
        "source_clock": str(source_clock),
        "causal_parent_ids": list(causal_parent_ids),
        "unit_refs": [ref.as_dict() for ref in canonical_refs],
    }
    expected_sha256 = sha256_json(payload)
    expected_id = sha256_json({
        "kind": "ExpectedObservationFrame.id",
        "monotonic_tick": int(monotonic_tick),
        "source_clock": str(source_clock),
        "expected_sha256": expected_sha256,
    })
    return ExpectedObservationFrame(
        expected_id=expected_id,
        monotonic_tick=int(monotonic_tick),
        source_clock=str(source_clock),
        unit_refs=canonical_refs,
        causal_parent_ids=tuple(causal_parent_ids),
        expected_sha256=expected_sha256,
    )


@dataclass(frozen=True, slots=True)
class ChangedSlot:
    """One slot whose compiled evidence changed."""

    slot_id: str
    expected_merge_key: MergeKey
    actual_merge_key: MergeKey

    def as_dict(self) -> dict[str, object]:
        return {
            "slot_id": self.slot_id,
            "expected_merge_key": _merge_key_record(self.expected_merge_key),
            "actual_merge_key": _merge_key_record(self.actual_merge_key),
        }


@dataclass(frozen=True, slots=True)
class FalsificationResidual:
    """Exact slot/set delta between expectation and observation."""

    matched: tuple[str, ...]
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]
    changed: tuple[ChangedSlot, ...]
    residual_sha256: str

    @property
    def is_supported(self) -> bool:
        return not self.missing and not self.unexpected and not self.changed

    def as_dict(self) -> dict[str, object]:
        return {
            "matched": list(self.matched),
            "missing": list(self.missing),
            "unexpected": list(self.unexpected),
            "changed": [change.as_dict() for change in self.changed],
            "residual_sha256": self.residual_sha256,
        }


@dataclass(frozen=True, slots=True)
class FalsificationRun:
    """Trace-safe result of one expected-vs-actual comparison."""

    expected_id: str
    actual_frame_id: str
    verdict: str
    residual: FalsificationResidual
    expected_sha256: str
    actual_trace_hash: str
    trace_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "expected_id": self.expected_id,
            "actual_frame_id": self.actual_frame_id,
            "verdict": self.verdict,
            "residual": self.residual.as_dict(),
            "expected_sha256": self.expected_sha256,
            "actual_trace_hash": self.actual_trace_hash,
            "trace_hash": self.trace_hash,
        }


def _refs_by_slot(refs: Iterable[ObservationUnitRef]) -> dict[str, ObservationUnitRef]:
    return {ref.slot_id: ref for ref in _canonical_refs(refs)}


def _actual_refs_from_frame(actual: ObservationFrame) -> tuple[ObservationUnitRef, ...]:
    return tuple(
        ObservationUnitRef(
            slot_id="unassigned:" + ":".join(unit.merge_key),
            unit=unit,
        )
        for unit in actual.units
    )


def compare_expected_to_observation(
    expected: ExpectedObservationFrame,
    actual: ObservationFrame,
    *,
    actual_refs: Iterable[ObservationUnitRef] | None = None,
) -> FalsificationRun:
    """Compare expected slot evidence with an actual afferent observation frame."""
    actual_ref_tuple = (
        _actual_refs_from_frame(actual)
        if actual_refs is None
        else _canonical_refs(actual_refs)
    )
    actual_frame_keys = {unit.merge_key for unit in actual.units}
    for ref in actual_ref_tuple:
        if ref.merge_key not in actual_frame_keys:
            raise ValueError(f"actual ref is not present in ObservationFrame: {ref.slot_id}")

    expected_by_slot = _refs_by_slot(expected.unit_refs)
    actual_by_slot = _refs_by_slot(actual_ref_tuple)
    for unit in actual.units:
        if unit.merge_key not in {ref.merge_key for ref in actual_ref_tuple}:
            synthetic = ObservationUnitRef(
                slot_id="unassigned:" + ":".join(unit.merge_key),
                unit=unit,
            )
            actual_by_slot[synthetic.slot_id] = synthetic

    matched: list[str] = []
    missing: list[str] = []
    changed: list[ChangedSlot] = []
    for slot_id, exp_ref in expected_by_slot.items():
        act_ref = actual_by_slot.get(slot_id)
        if act_ref is None:
            missing.append(slot_id)
        elif act_ref.merge_key == exp_ref.merge_key:
            matched.append(slot_id)
        else:
            changed.append(ChangedSlot(slot_id, exp_ref.merge_key, act_ref.merge_key))

    unexpected = sorted(set(actual_by_slot) - set(expected_by_slot))
    residual_payload = {
        "matched": sorted(matched),
        "missing": sorted(missing),
        "unexpected": unexpected,
        "changed": [change.as_dict() for change in sorted(changed, key=lambda c: c.slot_id)],
    }
    residual = FalsificationResidual(
        matched=tuple(residual_payload["matched"]),
        missing=tuple(residual_payload["missing"]),
        unexpected=tuple(unexpected),
        changed=tuple(sorted(changed, key=lambda c: c.slot_id)),
        residual_sha256=sha256_json(residual_payload),
    )
    verdict = "SUPPORTED" if residual.is_supported else "FALSIFIED"
    trace_payload = {
        "kind": "FalsificationRun",
        "expected_id": expected.expected_id,
        "actual_frame_id": actual.frame_id,
        "expected_sha256": expected.expected_sha256,
        "actual_trace_hash": actual.trace_hash,
        "verdict": verdict,
        "residual_sha256": residual.residual_sha256,
    }
    return FalsificationRun(
        expected_id=expected.expected_id,
        actual_frame_id=actual.frame_id,
        verdict=verdict,
        residual=residual,
        expected_sha256=expected.expected_sha256,
        actual_trace_hash=actual.trace_hash,
        trace_hash=sha256_json(trace_payload),
    )


__all__ = [
    "ChangedSlot",
    "ExpectedObservationFrame",
    "FalsificationResidual",
    "FalsificationRun",
    "ObservationUnitRef",
    "build_expected_observation_frame",
    "compare_expected_to_observation",
]
