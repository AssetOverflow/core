"""Offline JSONL witness-log importer.

Witness logs are evidence transport, not truth. The importer accepts only
payload references and uses a caller-provided resolver to obtain already
bounded afferent compilation units.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sensorium.audio.checksum import sha256_json
from sensorium.compiler.protocol import CompilationUnitLike
from sensorium.environment import ObservationFrame, ObservationUnitRef, build_observation_frame

_RAW_KEYS = {"pixels", "samples", "pcm", "waveform", "raw_bytes", "action_trace", "events"}
_LIVE_KEYS = {"device", "device_handle", "socket", "url", "network", "ros_node", "mcap_reader"}
_ALLOWED_MODALITIES = {"audio", "vision", "event-vision", "sensorimotor"}


@dataclass(frozen=True, slots=True)
class WitnessLogManifest:
    source_kind: str
    source_sha256: str
    schema_version: str
    record_count: int
    manifest_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind,
            "source_sha256": self.source_sha256,
            "schema_version": self.schema_version,
            "record_count": self.record_count,
            "manifest_sha256": self.manifest_sha256,
        }


@dataclass(frozen=True, slots=True)
class WitnessRecord:
    tick: int
    source_clock: str
    modality: str
    slot_id: str
    payload_ref: str
    provenance_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "tick": self.tick,
            "source_clock": self.source_clock,
            "modality": self.modality,
            "slot_id": self.slot_id,
            "payload_ref": self.payload_ref,
            "provenance_sha256": self.provenance_sha256,
        }


@dataclass(frozen=True, slots=True)
class ImportedObservationSequence:
    manifest: WitnessLogManifest
    frames: tuple[ObservationFrame, ...]
    frame_refs: tuple[tuple[str, tuple[ObservationUnitRef, ...]], ...]
    trace_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "manifest": self.manifest.as_dict(),
            "frames": [
                {
                    "frame_id": frame.frame_id,
                    "monotonic_tick": frame.monotonic_tick,
                    "source_clock": frame.source_clock,
                    "environment_sha256": frame.environment_sha256,
                    "trace_hash": frame.trace_hash,
                }
                for frame in self.frames
            ],
            "frame_refs": [
                {
                    "frame_id": frame_id,
                    "slots": [ref.slot_id for ref in refs],
                }
                for frame_id, refs in self.frame_refs
            ],
            "trace_hash": self.trace_hash,
        }


def _safe_ref(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if ".." in value or "/" in value or "\\" in value:
        raise ValueError(f"{field} must not contain path traversal")
    for ch in value:
        if not (ch.isascii() and (ch.isalnum() or ch in {"_", "-", ":", "."})):
            raise ValueError(f"{field} contains an unsafe character")
    return value


def _reject_raw_or_live(value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_str = str(key)
            if key_str in _RAW_KEYS:
                raise ValueError(f"witness trace record contains raw payload field: {key_str}")
            if key_str in _LIVE_KEYS:
                raise ValueError(f"witness trace record contains live device field: {key_str}")
            _reject_raw_or_live(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_raw_or_live(child)


def _record_from_mapping(row: Mapping[str, Any]) -> WitnessRecord:
    _reject_raw_or_live(row)
    tick = int(row["tick"])
    if tick < 0:
        raise ValueError("witness tick must be non-negative")
    modality = _safe_ref(row["modality"], field="modality")
    if modality not in _ALLOWED_MODALITIES:
        raise ValueError(f"unsupported witness modality: {modality}")
    slot_id = _safe_ref(row["slot_id"], field="slot_id")
    payload_ref = _safe_ref(row["payload_ref"], field="payload_ref")
    source_clock = _safe_ref(row.get("source_clock", "witness-jsonl"), field="source_clock")
    payload = {
        "kind": "WitnessRecord",
        "tick": tick,
        "source_clock": source_clock,
        "modality": modality,
        "slot_id": slot_id,
        "payload_ref": payload_ref,
    }
    return WitnessRecord(
        tick=tick,
        source_clock=source_clock,
        modality=modality,
        slot_id=slot_id,
        payload_ref=payload_ref,
        provenance_sha256=sha256_json(payload),
    )


def _build_manifest(
    records: tuple[WitnessRecord, ...],
    *,
    source_kind: str,
    schema_version: str,
) -> WitnessLogManifest:
    source_sha256 = sha256_json({
        "kind": "WitnessLog.source",
        "records": [record.as_dict() for record in records],
    })
    payload = {
        "kind": "WitnessLogManifest",
        "source_kind": source_kind,
        "source_sha256": source_sha256,
        "schema_version": schema_version,
        "record_count": len(records),
    }
    return WitnessLogManifest(
        source_kind=source_kind,
        source_sha256=source_sha256,
        schema_version=schema_version,
        record_count=len(records),
        manifest_sha256=sha256_json(payload),
    )


def import_witness_records(
    rows: Iterable[Mapping[str, Any]],
    *,
    resolve_payload_ref: Callable[[str], CompilationUnitLike],
    source_kind: str = "jsonl-witness-v1",
    schema_version: str = "1",
) -> ImportedObservationSequence:
    records = tuple(sorted(
        (_record_from_mapping(row) for row in rows),
        key=lambda record: (
            record.tick,
            record.source_clock,
            record.slot_id,
            record.payload_ref,
            record.provenance_sha256,
        ),
    ))
    manifest = _build_manifest(
        records,
        source_kind=_safe_ref(source_kind, field="source_kind"),
        schema_version=_safe_ref(schema_version, field="schema_version"),
    )
    by_frame: dict[tuple[int, str], list[WitnessRecord]] = defaultdict(list)
    for record in records:
        by_frame[(record.tick, record.source_clock)].append(record)

    frames: list[ObservationFrame] = []
    frame_refs: list[tuple[str, tuple[ObservationUnitRef, ...]]] = []
    for (tick, source_clock), frame_records in sorted(by_frame.items()):
        refs = tuple(
            ObservationUnitRef(record.slot_id, resolve_payload_ref(record.payload_ref))
            for record in frame_records
        )
        frame = build_observation_frame(
            monotonic_tick=tick,
            source_clock=source_clock,
            units=tuple(ref.unit for ref in refs),
            causal_parent_ids=(manifest.manifest_sha256,),
        )
        frames.append(frame)
        frame_refs.append((frame.frame_id, refs))

    trace_hash = sha256_json({
        "kind": "ImportedObservationSequence",
        "manifest_sha256": manifest.manifest_sha256,
        "frame_trace_hashes": [frame.trace_hash for frame in frames],
        "frame_ref_slots": [
            {"frame_id": frame_id, "slots": [ref.slot_id for ref in refs]}
            for frame_id, refs in frame_refs
        ],
    })
    return ImportedObservationSequence(
        manifest=manifest,
        frames=tuple(frames),
        frame_refs=tuple(frame_refs),
        trace_hash=trace_hash,
    )


def _validate_offline_path(path: Path) -> Path:
    if ".." in path.parts:
        raise ValueError("witness log path must not contain path traversal")
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return resolved


def import_witness_jsonl(
    path: str | Path,
    *,
    resolve_payload_ref: Callable[[str], CompilationUnitLike],
    schema_version: str = "1",
) -> ImportedObservationSequence:
    log_path = _validate_offline_path(Path(path))
    rows = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return import_witness_records(
        rows,
        resolve_payload_ref=resolve_payload_ref,
        source_kind="jsonl-witness-v1",
        schema_version=schema_version,
    )


__all__ = [
    "ImportedObservationSequence",
    "WitnessLogManifest",
    "WitnessRecord",
    "import_witness_jsonl",
    "import_witness_records",
]
